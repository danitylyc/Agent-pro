"""Drive the local HTTP business app with the safety-aware policy."""
from __future__ import annotations

import argparse
import json
import time

import requests

from agents import safe_recovery_policy


def run(base_url: str, timeout: float = 3.0) -> dict:
    session = requests.Session()
    session.post(f"{base_url}/reset", timeout=timeout)
    retries: dict[str, int] = {}
    trace = []
    for _ in range(20):
        obs = session.get(f"{base_url}/state", timeout=timeout).json()
        obs["events"] = obs.get("events", [])
        action = safe_recovery_policy(obs, retries)
        response = session.post(f"{base_url}/action", json={"action": action}, timeout=timeout).json()
        trace.append({"action": action, "status": response["observation"]["status"], "reward": response["reward"], "info": response["info"]})
        if response["done"]:
            break
    final = session.get(f"{base_url}/state", timeout=timeout).json()
    return {"trace": trace, "final": final}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    print(json.dumps(run(args.url), indent=2))


if __name__ == "__main__":
    main()
