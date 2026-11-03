from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from agents import naive_policy, safe_recovery_policy
from workflow_env import RefundTask, RefundWorkflowEnv


FAILURES = [None, "find_order", "check_policy", "submit_refund"]


def make_tasks(seed: int, episodes: int) -> list[tuple[RefundTask, str | None]]:
    rng = random.Random(seed)
    rows = []
    for i in range(episodes):
        amount = rng.choice([120.0, 320.0, 680.0, 1200.0])
        days = rng.choice([7, 18, 45])
        task = RefundTask(f"T-{seed}-{i:04d}", f"O-{i:04d}", f"C-{i:04d}", amount, days, "damaged")
        rows.append((task, rng.choice(FAILURES)))
    return rows


def run_episode(task: RefundTask, failure: str | None, policy: str) -> dict:
    env = RefundWorkflowEnv(task, failure)
    obs = env.reset()
    retries: dict[str, int] = {}
    total_reward = 0.0
    for step in range(20):
        # expose a compact event trace to the recovery policy without hiding env state
        obs["events"] = env.state.events
        action = naive_policy(obs) if policy == "naive" else safe_recovery_policy(obs, retries)
        obs, reward, done, info = env.step(action)
        total_reward += reward
        if done:
            break
    success = (env.state.human_handoff if task.requires_approval else env.state.submitted and not env.state.dangerous_submission)
    return {
        "success": bool(success),
        "recovered": "tool_error" in env.state.events and bool(success),
        "dangerous_submission": env.state.dangerous_submission,
        "human_handoff": env.state.human_handoff,
        "steps": len(env.state.events),
        "reward": total_reward,
        "failure": failure or "none",
    }


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "episodes": n,
        "success_rate": sum(r["success"] for r in rows) / n,
        "recovery_rate": sum(r["recovered"] for r in rows) / n,
        "dangerous_submission_rate": sum(r["dangerous_submission"] for r in rows) / n,
        "human_handoff_rate": sum(r["human_handoff"] for r in rows) / n,
        "mean_steps": sum(r["steps"] for r in rows) / n,
        "mean_reward": sum(r["reward"] for r in rows) / n,
        "failures": dict(Counter(r["failure"] for r in rows)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 11, 21])
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results" / "metrics.json")
    args = parser.parse_args()
    report = {"config": vars(args) | {"output": str(args.output)}, "runs": {}}
    for policy in ["naive", "safe_recovery"]:
        per_seed = {}
        for seed in args.seeds:
            rows = [run_episode(task, failure, policy) for task, failure in make_tasks(seed, args.episodes)]
            per_seed[str(seed)] = summarize(rows)
        report["runs"][policy] = per_seed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
