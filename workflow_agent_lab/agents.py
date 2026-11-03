"""Baseline and safety-aware policies for the refund workflow."""
from __future__ import annotations

from typing import Any


def naive_policy(obs: dict[str, Any]) -> str:
    sequence = {
        "start": "find_customer",
        "customer_found": "find_order",
        "order_found": "check_policy",
        "policy_checked": "draft_refund",
        "drafted": "submit_refund",
    }
    return sequence.get(obs["status"], "submit_refund")


def safe_recovery_policy(obs: dict[str, Any], retries: dict[str, int]) -> str:
    if obs["failure_type"]:
        action = obs["events"][-2] if "events" in obs and len(obs["events"]) > 1 else None
        if action and retries.get(action, 0) < 1:
            retries[action] = retries.get(action, 0) + 1
            return action
        return "recover"
    status = obs["status"]
    if status == "start":
        return "find_customer"
    if status == "customer_found":
        return "find_order"
    if status == "order_found":
        return "check_policy"
    if status == "policy_checked":
        return "draft_refund"
    if status == "drafted":
        return "request_approval" if obs["requires_approval"] else "submit_refund"
    return "recover"
