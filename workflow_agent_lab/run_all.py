"""Reproduce the complete local benchmark in one command."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).parent


def run_python(script: str, *args: str) -> None:
    command = [sys.executable, script, *args]
    subprocess.run(command, cwd=ROOT, check=True)


def wait_for_server(url: str, process: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"HTTP server exited with code {process.returncode}")
        try:
            requests.get(url, timeout=0.3)
            return
        except requests.RequestException:
            time.sleep(0.2)
    raise TimeoutError("HTTP server did not become ready")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "summary.json")
    args = parser.parse_args()
    run_python("evaluate.py", "--episodes", str(args.episodes), "--seeds", "7", "11", "21")
    run_python("offline_rl.py", "--episodes", str(args.episodes), "--seeds", "7", "11", "21")
    run_python("robustness.py", "--episodes", str(args.episodes), "--seed", "101")

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "web_app:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server("http://127.0.0.1:8765/", server)
        run_python("http_eval.py", "--url", "http://127.0.0.1:8765", "--episodes", str(args.episodes), "--seed", "17")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

    files = {
        "local_metrics": ROOT / "results" / "metrics.json",
        "offline_rl": ROOT / "results" / "offline_rl.json",
        "robustness": ROOT / "results" / "robustness.json",
        "http_eval": ROOT / "results" / "http_eval.json",
    }
    report = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in files.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
