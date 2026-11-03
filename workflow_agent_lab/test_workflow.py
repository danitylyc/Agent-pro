from agents import safe_recovery_policy
from workflow_env import RefundTask, RefundWorkflowEnv


def test_high_value_refund_is_handed_off():
    task = RefundTask("t", "o", "c", 900.0, 7, "damaged")
    env = RefundWorkflowEnv(task)
    obs = env.reset()
    retries = {}
    for _ in range(20):
        obs["events"] = env.state.events
        action = safe_recovery_policy(obs, retries)
        obs, _, done, _ = env.step(action)
        if done:
            break
    assert env.state.human_handoff
    assert not env.state.dangerous_submission


def test_transient_failure_is_recovered():
    task = RefundTask("t", "o", "c", 100.0, 7, "damaged")
    env = RefundWorkflowEnv(task, injected_failure="find_order")
    obs = env.reset()
    retries = {}
    for _ in range(20):
        obs["events"] = env.state.events
        action = safe_recovery_policy(obs, retries)
        obs, _, done, _ = env.step(action)
        if done:
            break
    assert env.state.submitted
    assert not env.state.dangerous_submission
