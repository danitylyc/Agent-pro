"""Offline action learning for the refund workflow.

This is intentionally tabular: the environment is finite, so every decision
can be inspected.  It implements fitted Q iteration with a conservative
penalty for actions that are rare or absent in the logged data.  The same
interface can later be replaced by a neural action scorer without changing the
environment or evaluation protocol.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agents import naive_policy, safe_recovery_policy
from evaluate import make_tasks
from workflow_env import RefundTask, RefundWorkflowEnv

ACTIONS = [
    "find_customer",
    "find_order",
    "check_policy",
    "draft_refund",
    "submit_refund",
    "request_approval",
    "recover",
]


def state_key(obs: dict[str, Any]) -> str:
    return "|".join(
        [
            str(obs["status"]),
            "approval" if obs["requires_approval"] else "normal",
            str(obs.get("failure_type") or "none"),
        ]
    )


def collect(seed: int, episodes: int, policy: str = "expert", output: Path | None = None) -> list[dict[str, Any]]:
    """Collect trajectories, retaining every transition for auditing.

    ``expert`` is the safety-aware policy; ``naive`` deliberately provides
    lower-quality demonstrations so the offline learner must handle behavior
    policy bias instead of merely memorising one clean trajectory.
    """
    transitions: list[dict[str, Any]] = []
    for task, failure in make_tasks(seed, episodes):
        env = RefundWorkflowEnv(task, failure)
        obs = env.reset()
        retries: dict[str, int] = {}
        for _ in range(20):
            obs["events"] = env.state.events
            action = safe_recovery_policy(obs, retries) if policy == "expert" else naive_policy(obs)
            before = state_key(obs)
            next_obs, reward, done, info = env.step(action)
            transitions.append(
                {
                    "task_id": task.task_id,
                    "state": before,
                    "action": action,
                    "next_state": state_key(next_obs),
                    "reward": reward,
                    "done": done,
                    "failure": failure or "none",
                    "behavior_policy": policy,
                    "info": info,
                }
            )
            obs = next_obs
            if done:
                break
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(json.dumps(row) for row in transitions) + "\n", encoding="utf-8")
    return transitions


def train_cql(transitions: list[dict[str, Any]], iterations: int = 30, alpha: float = 0.25) -> tuple[dict[str, dict[str, float]], dict[str, Counter]]:
    """Fit a small conservative Q table from logged transitions."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for row in transitions:
        counts[row["state"]][row["action"]] += 1
    q: dict[str, dict[str, float]] = defaultdict(lambda: {a: -alpha for a in ACTIONS})
    gamma = 0.95
    for _ in range(iterations):
        updated: dict[str, dict[str, float]] = defaultdict(lambda: {a: -alpha for a in ACTIONS})
        for row in transitions:
            action_count = counts[row["state"]][row["action"]]
            # Conservative penalty is stronger for actions seen only once.
            pessimism = alpha / math.sqrt(action_count)
            if row["done"]:
                target = row["reward"]
            else:
                target = row["reward"] + gamma * max(q[row["next_state"]].values())
            old = q[row["state"]][row["action"]]
            updated[row["state"]][row["action"]] = (1 - 0.2) * old + 0.2 * (target - pessimism)
        q = updated
    return q, counts


def train_bc(transitions: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Return a deterministic behavior-cloning policy from action frequencies."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for row in transitions:
        counts[row["state"]][row["action"]] += 1
    return {
        state: {action: float(counter.get(action, 0)) for action in ACTIONS}
        for state, counter in counts.items()
    }


def choose(q: dict[str, dict[str, float]], obs: dict[str, Any]) -> str:
    key = state_key(obs)
    values = q.get(key)
    if values is None:
        # Conservative fallback is deliberately safe for unseen states.
        if obs.get("failure_type"):
            return str(obs["failure_type"]).replace("transient_", "")
        return "request_approval" if obs["requires_approval"] and obs["status"] == "drafted" else {
            "start": "find_customer", "customer_found": "find_order",
            "order_found": "check_policy", "policy_checked": "draft_refund",
            "drafted": "submit_refund",
        }.get(obs["status"], "recover")
    return max(values, key=values.get)


def evaluate(q: dict[str, dict[str, float]], seed: int, episodes: int) -> dict[str, float]:
    rows = []
    for task, failure in make_tasks(seed, episodes):
        env = RefundWorkflowEnv(task, failure)
        obs = env.reset()
        for _ in range(20):
            action = choose(q, obs)
            obs, reward, done, _ = env.step(action)
            if done:
                break
        success = env.state.human_handoff if task.requires_approval else env.state.submitted and not env.state.dangerous_submission
        rows.append((bool(success), env.state.dangerous_submission, len(env.state.events)))
    return {
        "success_rate": sum(x[0] for x in rows) / len(rows),
        "dangerous_submission_rate": sum(x[1] for x in rows) / len(rows),
        "mean_steps": sum(x[2] for x in rows) / len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 11, 21])
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results" / "offline_rl.json")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parent / "results" / "trajectories.jsonl")
    args = parser.parse_args()
    all_transitions = []
    for seed in args.seeds:
        # Deliberately oversample the lower-quality behavior policy. This
        # creates a meaningful offline-data-bias test for the ablation table.
        all_transitions.extend(collect(seed, args.episodes, policy="expert"))
        for offset in range(3):
            all_transitions.extend(collect(seed + 1000 + offset, args.episodes, policy="naive"))
    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    args.dataset.write_text("\n".join(json.dumps(row) for row in all_transitions) + "\n", encoding="utf-8")
    q, counts = train_cql(all_transitions, alpha=0.25)
    q_no_conservative, _ = train_cql(all_transitions, alpha=0.0)
    bc = train_bc(all_transitions)
    report = {
        "algorithm": "tabular fitted Q iteration with conservative penalty",
        "transitions": len(all_transitions),
        "states": len(q),
        "action_coverage": sum(len(v) for v in counts.values()) / max(len(counts), 1),
        "behavior_policy_mix": dict(Counter(row["behavior_policy"] for row in all_transitions)),
        "evaluation": {
            "behavior_cloning": {str(seed): evaluate(bc, seed, args.episodes) for seed in args.seeds},
            "fitted_q_no_conservative": {str(seed): evaluate(q_no_conservative, seed, args.episodes) for seed in args.seeds},
            "fitted_q_conservative": {str(seed): evaluate(q, seed, args.episodes) for seed in args.seeds},
        },
    }
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
