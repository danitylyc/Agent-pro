# Agent-pro

A portfolio of **auditable agent experiments** — three self-contained labs that turn "agents for real workflows" into reproducible, locally verifiable problems. No cloud model, no real business data, no unverifiable benchmark claims: every number below is produced by the checked-in scripts on a local simulator.

The main project is [`workflow_agent_lab`](workflow_agent_lab/) — a **safe long-horizon agent for an enterprise refund workflow**. `coding_agent_lab` and `offline_rl_lab` are kept as method baselines.

## Labs at a glance

| lab | question | stack | status |
|---|---|---|---|
| [`workflow_agent_lab`](workflow_agent_lab/) | Can an agent complete a long business workflow under tool failures, policy constraints and high-risk submissions — without committing dangerous actions? | Python-only local environment, rule-based strategies, tabular offline RL | **main project, fully evaluated** |
| [`offline_rl_lab`](offline_rl_lab/) | Can offline RL recover from biased/low-quality data on a sparse-reward environment? | CleanRL-style + Minari-style interfaces, tabular BC vs CQL | baseline experiments done |
| [`coding_agent_lab`](coding_agent_lab/) | Reproducing a minimal coding agent (mini-SWE-agent) as an auditable baseline | `mini-swe-agent` 2.4.6 (Python 3.11) | setup complete, experiments next |

## Main project — `workflow_agent_lab`

A safe long-horizon agent testbed for an **enterprise refund process**. Each task contains a customer, order, refund reason and amount; the agent must query the order, check the refund policy, fill the refund form, and escalate to human approval when the amount exceeds a threshold or the order is stale. The environment randomly injects tool failures and state inconsistencies, testing whether the agent verifies state, retries, and recovers.

Two comparable strategies:

- `naive` — fixed-order execution, fails on first error;
- `safe_recovery` — explicit task-state maintenance, verification after every critical action, risk-rule escalation, bounded retries on recoverable errors.

### Results (3 seeds × 30 episodes, local simulator; from `results/summary.json`)

| evaluation | naive | safe_recovery |
|---|---|---|
| local, 3 seeds | success 0.20–0.30, dangerous submission 0.70–0.80 | **success 1.00**, **dangerous submission 0.00**, human handoff 0.70–0.80, ≈5.8–5.9 steps |
| dual-fault stress (2 independent failures per task, 30 eps) | success 0.40, dangerous submission 0.60 | **success 1.00**, **dangerous submission 0.00**, ≈8.3 steps |
| HTTP integration (30 eps, all state/actions through the HTTP interface) | — | **success 1.00**, **dangerous submission 0.00**, 5.47 steps |

The dual-fault stress test exists to show the recovery strategy is not overfit to a single failure type.

### Offline RL loop (included in the same lab)

`offline_rl.py` exports agent trajectories to offline data and trains an action policy from them: 2,045 transitions (16 states) mixing the safe policy with low-quality fixed-order trajectories (3:1 oversample). Tabular fitted Q iteration with a conservative penalty:

| policy | success rate | dangerous submission rate |
|---|---|---|
| behavior cloning | 0.20–0.30 | 0.70–0.80 |
| fitted Q (with / without conservative penalty) | **1.00** | **0.00** |

This shows the environment's reward and termination signals can correct behavior-data bias — and is an auditable minimal closed loop for a neural action scorer / offline RL next step.

### HTTP boundary

`web_app.py` serves a local business page with status/action/reset endpoints; `http_agent.py` (and a `selenium_agent.py` DOM adapter) drive it through real HTTP requests. The HTTP integration eval (30 tasks, all via reset/state/action interfaces) achieves success 1.00 with 0 dangerous submissions — not a direct call into the Python environment object. Browser execution is not claimed as a verified result on machines missing a matching `msedgedriver`; the adapter fails loudly instead of faking results.

## Quick reproduction

```powershell
py -3.11 run_all.py --episodes 30
```

Runs the local baseline, the mixed-data offline RL, the dual-fault stress test and the HTTP integration eval in sequence (auto-starts and cleans up the temporary uvicorn server), and writes `results/summary.json`.

Individual entries:

```powershell
py -3.11 evaluate.py --episodes 100 --seeds 7 11 21        # local baseline
py -3.11 robustness.py --episodes 100 --seed 101           # dual-fault stress
py -3.11 offline_rl.py --episodes 100 --seeds 7 11 21      # offline RL loop
py -3.11 -m uvicorn web_app:app --host 127.0.0.1 --port 8765   # + http_agent.py / http_eval.py
py -3.11 demo.py --amount 900 --failure find_order         # structured-action demo
```

## Repository layout

```
Agent-pro/
├── PROJECT_SELECTION.md        # problem selection & roadmap (Chinese)
├── workflow_agent_lab/         # main project: safe refund-workflow agent
│   ├── workflow_env.py         #   task generator + fault injection environment
│   ├── agents.py               #   naive / safe_recovery strategies
│   ├── evaluate.py             #   3-seed evaluation → results/metrics.json
│   ├── robustness.py           #   dual-fault stress test
│   ├── offline_rl.py           #   trajectory export + tabular offline RL
│   ├── web_app.py              #   local HTTP business page
│   ├── http_agent.py / http_eval.py / selenium_agent.py   #   interaction adapters
│   ├── run_all.py              #   one-command reproduction → results/summary.json
│   ├── ARCHITECTURE.md / RESUME_BULLETS.md
│   └── results/                # metrics.json, summary.json, trajectories.jsonl, …
├── offline_rl_lab/             # CleanRL+Minari-style offline RL baseline (ChainEnv)
│   ├── train_offline.py        #   tabular BC vs CQL, 3 seeds
│   └── results/metrics.json    #   BC −0.20 vs CQL 0.96 (+1.16)
└── coding_agent_lab/           # mini-SWE-agent reproduction entry
    ├── smoke_test.py           #   version/import check
    └── requirements.txt
```

## Honest boundaries

- All results come from a **local simulator** — they are not real business metrics and are not presented as public benchmark scores.
- `coding_agent_lab` currently only pins and imports the upstream package; task-level results will be measured on a fixed offline task set (upstream's SWE-bench claims are not reproduced).
- The offline-RL lab is a small tabular experiment demonstrating the data-bias → conservative Q-learning → independent-eval chain, not a MuJoCo/D4RL-scale result.

## License & attribution

This repository adds new experimental code only; no real customer data. Upstream references: [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) (MIT), [CleanRL](https://github.com/vwxyzjn/cleanrl) (MIT), [Minari](https://github.com/Farama-Foundation/Minari) (Apache-2.0).
