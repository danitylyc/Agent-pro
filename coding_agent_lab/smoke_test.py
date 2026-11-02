"""Dependency and version smoke test for the upstream coding-agent baseline."""
from __future__ import annotations

import json

import minisweagent


def main() -> None:
    expected = "2.4.6"
    actual = minisweagent.__version__
    report = {
        "package": "mini-swe-agent",
        "expected_version": expected,
        "actual_version": actual,
        "import_ok": True,
        "version_ok": actual == expected,
    }
    print(json.dumps(report, indent=2))
    if actual != expected:
        raise SystemExit(f"version mismatch: expected {expected}, got {actual}")


if __name__ == "__main__":
    main()
