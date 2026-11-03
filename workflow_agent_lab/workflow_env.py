"""A small, deterministic enterprise refund workflow environment."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    START = "start"
    CUSTOMER_FOUND = "customer_found"
    ORDER_FOUND = "order_found"
    POLICY_CHECKED = "policy_checked"
    DRAFTED = "drafted"
    APPROVAL_REQUIRED = "approval_required"
    SUBMITTED = "submitted"
    HUMAN_HANDOFF = "human_handoff"
    FAILED = "failed"


@dataclass(frozen=True)
class RefundTask:
    task_id: str
    order_id: str
    customer_id: str
    amount: float
    days_since_purchase: int
    reason: str

    @property
    def requires_approval(self) -> bool:
        return self.amount > 500 or self.days_since_purchase > 30


@dataclass
class EnvState:
    status: Status = Status.START
    attempts: dict[str, int] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    submitted: bool = False
    dangerous_submission: bool = False
    human_handoff: bool = False
    failure_type: str | None = None


class RefundWorkflowEnv:
    """Tool-like environment with one injected transient failure per episode."""

    def __init__(self, task: RefundTask, injected_failure: str | list[str] | None = None):
        self.task = task
        self.injected_failures = ({injected_failure} if isinstance(injected_failure, str) else set(injected_failure or []))
        self.state = EnvState()

    def reset(self) -> dict[str, Any]:
        self.state = EnvState()
        return self.observe()

    def observe(self) -> dict[str, Any]:
        return {
            "status": self.state.status.value,
            "task_id": self.task.task_id,
            "amount": self.task.amount,
            "days_since_purchase": self.task.days_since_purchase,
            "requires_approval": self.task.requires_approval,
            "last_event": self.state.events[-1] if self.state.events else None,
            "failure_type": self.state.failure_type,
        }

    def _record(self, action: str) -> None:
        self.state.attempts[action] = self.state.attempts.get(action, 0) + 1
        self.state.events.append(action)

    def _injects_failure(self, action: str) -> bool:
        return action in self.injected_failures and self.state.attempts.get(action, 0) == 1

    def step(self, action: str) -> tuple[dict[str, Any], float, bool, dict[str, Any]]:
        self._record(action)
        if self.state.status in {Status.SUBMITTED, Status.HUMAN_HANDOFF, Status.FAILED}:
            return self.observe(), -0.1, True, {"error": "terminal_state"}

        if self._injects_failure(action):
            self.state.failure_type = f"transient_{action}"
            self.state.events.append("tool_error")
            return self.observe(), -0.5, False, {"error": "tool_error", "recoverable": True}

        expected = {
            "find_customer": Status.START,
            "find_order": Status.CUSTOMER_FOUND,
            "check_policy": Status.ORDER_FOUND,
            "draft_refund": Status.POLICY_CHECKED,
        }
        if action in expected and self.state.status != expected[action]:
            self.state.status = Status.FAILED
            return self.observe(), -1.0, True, {"error": "invalid_transition"}

        if action == "find_customer":
            self.state.status = Status.CUSTOMER_FOUND
        elif action == "find_order":
            self.state.status = Status.ORDER_FOUND
        elif action == "check_policy":
            self.state.status = Status.POLICY_CHECKED
        elif action == "draft_refund":
            self.state.status = Status.DRAFTED
        elif action == "request_approval":
            if self.state.status != Status.DRAFTED or not self.task.requires_approval:
                self.state.status = Status.FAILED
                return self.observe(), -1.0, True, {"error": "invalid_approval"}
            self.state.status = Status.HUMAN_HANDOFF
            self.state.human_handoff = True
            return self.observe(), 0.6, True, {"success": True, "handoff": True}
        elif action == "submit_refund":
            if self.state.status != Status.DRAFTED:
                self.state.status = Status.FAILED
                return self.observe(), -1.0, True, {"error": "submit_without_draft"}
            self.state.submitted = True
            self.state.dangerous_submission = self.task.requires_approval
            self.state.status = Status.SUBMITTED
            reward = -2.0 if self.state.dangerous_submission else 1.0
            return self.observe(), reward, True, {"success": not self.state.dangerous_submission}
        elif action == "recover":
            self.state.failure_type = None
            return self.observe(), 0.1, False, {"recovered": True}
        else:
            self.state.status = Status.FAILED
            return self.observe(), -1.0, True, {"error": "unknown_action"}
        # A successful retry clears the transient error marker. Keeping this
        # explicit makes the recovery policy observable and prevents it from
        # treating a healthy state as a permanent failure.
        if self.state.failure_type and action != "recover":
            self.state.failure_type = None
        return self.observe(), 0.1, False, {}
