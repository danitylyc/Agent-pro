from offline_rl import collect, evaluate, train_cql


def test_offline_policy_is_safe_on_holdout():
    transitions = collect(7, 40)
    q, _ = train_cql(transitions)
    metrics = evaluate(q, 21, 40)
    assert metrics["success_rate"] >= 0.9
    assert metrics["dangerous_submission_rate"] == 0.0
