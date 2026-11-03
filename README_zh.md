# Agent-pro

一个**可审计的 Agent 实验合集**——三个自包含的实验室，把"为真实业务流程做 Agent"变成可复现、可在本地验证的问题。无云端模型、无真实业务数据、无无法核验的 benchmark 宣称：文中每个数字都由仓库内脚本在本地模拟器上实测产出。

主项目是 [`workflow_agent_lab`](workflow_agent_lab/)——一个面向**企业退款流程的安全长程 Agent**。`coding_agent_lab` 与 `offline_rl_lab` 保留为方法基线。

## 三个实验室一览

| 实验室 | 研究问题 | 技术栈 | 状态 |
|---|---|---|---|
| [`workflow_agent_lab`](workflow_agent_lab/) | 在工具故障、策略约束与高风险提交并存时，Agent 能否完成任务而不产生危险操作？ | 纯 Python 本地环境、规则策略、tabular 离线 RL | **主项目，已完成评估** |
| [`offline_rl_lab`](offline_rl_lab/) | 稀疏奖励环境下，离线 RL 能否从有偏差/低质量数据中恢复？ | CleanRL 风格 + Minari 风格接口，tabular BC vs CQL | 基线实验已完成 |
| [`coding_agent_lab`](coding_agent_lab/) | 复现极简 coding agent（mini-SWE-agent）作为可审计基线 | `mini-swe-agent` 2.4.6（Python 3.11） | 环境搭建完成，实验待做 |

## 主项目 —— `workflow_agent_lab`

面向**企业退款流程**的安全长程 Agent 实验台。每个任务包含客户、订单、退款原因和金额；Agent 需要查询订单、检查退款政策、填写退款单，并在金额超阈值或订单过期时转人工审批。环境随机注入工具故障与状态不一致，考察 Agent 是否验证状态、重试并恢复。

两个可对照策略：

- `naive` —— 固定顺序执行，遇到错误直接失败；
- `safe_recovery` —— 显式维护任务状态，在每个关键动作后验证，按风险规则转人工，对可恢复错误做有限重试。

### 结果（3 seeds × 30 episodes，本地模拟器；取自 `results/summary.json`）

| 评测 | naive | safe_recovery |
|---|---|---|
| 本地 3 seeds | 成功率 0.20–0.30，危险提交率 0.70–0.80 | **成功率 1.00**，**危险提交率 0.00**，人工介入率 0.70–0.80，约 5.8–5.9 步 |
| 双故障压力（每任务注入 2 个独立故障，30 回合） | 成功率 0.40，危险提交率 0.60 | **成功率 1.00**，**危险提交率 0.00**，约 8.3 步 |
| HTTP 集成评测（30 回合，全部状态/动作经 HTTP 接口） | — | **成功率 1.00**，**危险提交率 0.00**，平均 5.47 步 |

双故障压力测试的存在，是为了证明恢复策略不是对单一故障类型过拟合。

### 离线 RL 闭环（位于同一实验室）

`offline_rl.py` 把 Agent 轨迹导出为离线数据并从中训练动作策略：2,045 条转移（16 个状态），按 3:1 混合安全策略与低质量固定顺序轨迹。使用带保守惩罚的 tabular fitted Q iteration：

| 策略 | 成功率 | 危险提交率 |
|---|---|---|
| 行为克隆 | 0.20–0.30 | 0.70–0.80 |
| fitted Q（含/不含保守惩罚） | **1.00** | **0.00** |

这证明环境中的奖励与终止信号可以纠正行为数据偏差——也是后续神经 action scorer / offline RL 的最小可审计闭环。

### HTTP 边界

`web_app.py` 提供带状态/动作/重置端点的本地业务页面；`http_agent.py`（以及 `selenium_agent.py` DOM 适配器）通过真实 HTTP 请求驱动它。HTTP 集成评测（30 个任务，全部经 reset/state/action 接口）达到成功率 1.00、危险提交率 0——不是直接调用 Python 环境对象。缺少匹配 `msedgedriver` 的机器上，浏览器端执行不会被冒充为已验证结果；适配器会明确报错而不是伪造成绩。

## 快速复现

```powershell
py -3.11 run_all.py --episodes 30
```

依次运行本地 baseline、混合数据离线 RL、双故障压力测试和 HTTP 集成评测（自动启动并在结束时关闭临时 uvicorn 服务），输出 `results/summary.json`。

单项入口：

```powershell
py -3.11 evaluate.py --episodes 100 --seeds 7 11 21        # 本地 baseline
py -3.11 robustness.py --episodes 100 --seed 101           # 双故障压力
py -3.11 offline_rl.py --episodes 100 --seeds 7 11 21      # 离线 RL 闭环
py -3.11 -m uvicorn web_app:app --host 127.0.0.1 --port 8765   # + http_agent.py / http_eval.py
py -3.11 demo.py --amount 900 --failure find_order         # 结构化动作演示
```

## 目录结构

```
Agent-pro/
├── PROJECT_SELECTION.md        # 项目选择与路线（中文）
├── workflow_agent_lab/         # 主项目：安全退款流程 Agent
│   ├── workflow_env.py         #   任务生成器 + 故障注入环境
│   ├── agents.py               #   naive / safe_recovery 策略
│   ├── evaluate.py             #   3 种子评测 → results/metrics.json
│   ├── robustness.py           #   双故障压力测试
│   ├── offline_rl.py           #   轨迹导出 + tabular 离线 RL
│   ├── web_app.py              #   本地 HTTP 业务页面
│   ├── http_agent.py / http_eval.py / selenium_agent.py   #   交互适配器
│   ├── run_all.py              #   一键复现 → results/summary.json
│   ├── ARCHITECTURE.md / RESUME_BULLETS.md
│   └── results/                # metrics.json, summary.json, trajectories.jsonl, …
├── offline_rl_lab/             # CleanRL+Minari 风格离线 RL 基线（ChainEnv）
│   ├── train_offline.py        #   tabular BC vs CQL，3 种子
│   └── results/metrics.json    #   BC −0.20 vs CQL 0.96（+1.16）
└── coding_agent_lab/           # mini-SWE-agent 复现入口
    ├── smoke_test.py           #   版本/导入检查
    └── requirements.txt
```

## 诚实的边界

- 所有结果来自**本地模拟器**——不是真实业务指标，也不作为公开 benchmark 成绩展示。
- `coding_agent_lab` 目前只完成了上游包安装与导入检查；任务级结果将在固定离线任务集上重新测量（不复制上游的 SWE-bench 宣称成绩）。
- 离线 RL 实验室是一个小型 tabular 实验，展示"数据偏差 → 保守 Q 学习 → 独立评估"链路，不是 MuJoCo/D4RL 规模的结果。

## 许可与归属

本仓库只新增实验代码，不含真实客户数据。上游参考：[mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)（MIT）、[CleanRL](https://github.com/vwxyzjn/cleanrl)（MIT）、[Minari](https://github.com/Farama-Foundation/Minari)（Apache-2.0）。
