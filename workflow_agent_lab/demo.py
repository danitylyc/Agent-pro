"""Run one human-readable workflow episode for a portfolio demo."""
from __future__ import annotations

import argparse
import json

from agents import safe_recovery_policy
from workflow_env import RefundTask, RefundWorkflowEnv


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe refund workflow Agent demo")
    parser.add_argument("--amount", type=float, default=900.0)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--failure", choices=["none", "find_order", "check_policy", "submit_refund"], default="find_order")
    args = parser.parse_args()
    task = RefundTask("DEMO-1", "ORDER-1", "CUSTOMER-1", args.amount, args.days, "damaged")
    env = RefundWorkflowEnv(task, None if args.failure == "none" else args.failure)
    obs = env.reset()
    retries: dict[str, int] = {}
    trace = []
    for step in range(20):
        obs["events"] = env.state.events
        action = safe_recovery_policy(obs, retries)
        before = obs.copy()
        obs, reward, done, info = env.step(action)
        trace.append({"step": step + 1, "status_before": before["status"], "action": action, "status_after": obs["status"], "reward": reward, "info": info})
        if done:
            break
    print(json.dumps({"task": task.__dict__, "requires_approval": task.requires_approval, "trace": trace, "final": env.observe()}, indent=2))


if __name__ == "__main__":
    main()
