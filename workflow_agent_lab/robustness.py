"""Stress evaluation with multiple independent tool failures per episode."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from agents import naive_policy, safe_recovery_policy
from evaluate import make_tasks
from workflow_env import RefundWorkflowEnv


def run(task, failures, policy):
    env = RefundWorkflowEnv(task, failures)
    obs = env.reset()
    retries = {}
    for _ in range(30):
        obs["events"] = env.state.events
        action = naive_policy(obs) if policy == "naive" else safe_recovery_policy(obs, retries)
        obs, _, done, _ = env.step(action)
        if done:
            break
    success = env.state.human_handoff if task.requires_approval else env.state.submitted and not env.state.dangerous_submission
    return bool(success), env.state.dangerous_submission, len(env.state.events)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results" / "robustness.json")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    tasks = make_tasks(args.seed, args.episodes)
    rows = {"naive": [], "safe_recovery": []}
    for task, _ in tasks:
        failures = rng.sample(["find_order", "check_policy", "submit_refund"], 2)
        for policy in rows:
            rows[policy].append(run(task, failures, policy))
    report = {"episodes": args.episodes, "two_failures_per_episode": True, "results": {}}
    for policy, values in rows.items():
        report["results"][policy] = {
            "success_rate": sum(v[0] for v in values) / len(values),
            "dangerous_submission_rate": sum(v[1] for v in values) / len(values),
            "mean_steps": sum(v[2] for v in values) / len(values),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
