# Agent-pro 项目选择与可落地路线

本仓库的主线改为“真实问题 + 可验证环境 + 方法对照 + 可扩展模型”。`workflow_agent_lab` 是当前主项目；原有 coding-agent 和 offline-RL 目录保留为基线/方法实验，不把简单复现当作最终项目。

## 当前主项目：`workflow_agent_lab`

面向企业退款流程的安全长程 Agent。它研究工具故障、业务策略和高风险提交同时存在时，Agent 如何完成任务并避免危险操作。目录包含本地任务生成器、故障注入环境、`naive` 与 `safe_recovery` 对照策略、自动评分和单元测试。

第一轮 3 seeds × 30 episodes 的结果：`safe_recovery` 成功率为 1.00，危险提交率为 0；固定顺序 baseline 成功率约 0.20～0.30，危险提交率约 0.70～0.80。结果来自本地模拟器，不冒充真实业务或公开 benchmark 成绩。

后续将把轨迹导出为离线数据，训练 action scorer/offline RL 策略，再接入浏览器 UI；这样项目的贡献点是安全长程决策和失败恢复，而不是只换一个模型。

当前已完成混合质量离线闭环：按 3:1 混合安全策略与固定顺序策略，共采集 2045 条轨迹。行为克隆在 3 个独立 seed 上成功率约 0.20～0.30、危险提交率约 0.70～0.80；fitted Q（含/不含 conservative penalty）均达到 1.00 成功率和 0 危险提交率。该结果证明环境中的奖励与终止信号可以纠正行为数据偏差，但也说明需要下一阶段加入更强的 OOD 动作和页面扰动，才能区分两种 Q 学习变体。

另外增加了双故障压力测试：每个任务同时注入两个独立工具故障，`safe_recovery` 成功率 1.00、危险提交率 0；`naive` 成功率 0.45、危险提交率 0.55。这个结果用于验证恢复策略并非只针对单个故障编写。

已增加本地 HTTP 业务页面：`web_app.py` 提供状态查询、动作提交和重置接口，`http_agent.py` 通过真实 HTTP 请求完成一次含故障恢复和人工审批的流程。这样后续接入 Playwright/BrowserGym 时只替换交互适配器，不需要重写任务环境、风险规则和评测器。

HTTP 集成评测已支持动态金额、账龄和故障组合。30 个任务全部通过 HTTP reset/state/action 接口完成，成功率 1.00，危险提交率 0，平均 5.47 步；这不是直接调用 Python 环境对象的离线结果。

页面已加入真实 DOM 按钮和状态 JSON，并新增 `selenium_agent.py` 适配器。当前机器检测到 Edge 和 Selenium，但缺少匹配的 `msedgedriver`，因此浏览器端执行尚未作为已验证结果；HTTP 端仍是已验证路径。适配器已对驱动缺失给出明确错误，不会把失败伪装成评测结果。

已新增 `run_all.py` 一键复现实验入口，自动运行四类评测、启动并清理 HTTP 服务，生成 `results/summary.json`，降低项目交接和面试现场复现成本。

一键入口已在本机以 10 episodes 运行通过：本地安全策略 3 seeds 成功率均为 1.00，双故障压力测试成功率 1.00，HTTP 集成评测成功率 1.00；临时 uvicorn 服务在流程结束后已自动关闭。

## 候选与最终选择

### Agent：mini-SWE-agent → `coding_agent_lab`

上游：[SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)

选择理由：MIT 许可、核心 Agent loop 极简、只依赖 bash 工具、支持本地模型和 Python API，适合作为可审计的 coding-agent 基线。上游 README 报告其在 SWE-bench Verified 上超过 74%，但本项目不会直接复述该成绩，而是在固定本地任务集上重新测量。

本项目的改进假设：

1. 在每轮 shell 执行前加入“测试优先”的状态检查，减少无效探索。
2. 增加失败命令分类和有限重试策略，比较 baseline 与 recovery 版本的任务完成率、平均步数和 token/命令开销。
3. 使用 10～20 个离线 Python 修复任务作为可重复 smoke benchmark，不依赖在线 SWE-bench 或云端模型。

### 强化学习：CleanRL + Minari → `offline_rl_lab`

上游：[vwxyzjn/cleanrl](https://github.com/vwxyzjn/cleanrl) 与 [Farama-Foundation/Minari](https://github.com/Farama-Foundation/Minari)

选择理由：CleanRL 提供单文件、易审计的 PPO/DQN/SAC 等实现；Minari 提供标准化离线 RL 数据集接口。两者结合可以形成“数据读取—行为策略—离线训练—独立评估”的完整实验链，成本低于大规模 MuJoCo 项目。

本项目的改进假设：

1. 先用 Minari/Gymnasium 生成小型离线数据集，复现 Behavior Cloning 与 Conservative Q-Learning 基线。
2. 加入 advantage-weighted behavior cloning 或 conservative penalty schedule，测量平均回报、数据利用率和 OOD action rate。
3. 固定 3 个 seed，并保留原始数据、配置、曲线和消融表，避免只报告单次训练结果。

## 暂不选择

- OGBench：研究价值高，但 JAX + MuJoCo + 大规模数据集的本地成本较高，作为第二阶段扩展。
- PufferLib：吞吐量和多智能体能力很强，但更适合已有 GPU/CUDA 实验环境，不作为第一版主项目。
- E2E-SWE：任务规模和许可证限制不利于第一版本地复现，先采用 mini-SWE-agent 的小型离线任务集。

## 简历交付标准

- 每个项目都能从全新环境一条命令运行 smoke test。
- 至少有 baseline、optimized、ablation 三组结果。
- 至少 3 个随机种子，报告均值和标准差。
- README 写清上游来源、改动边界、数据许可、复现命令和结果。
- 最终推送到 `https://github.com/danitylyc/Agent-pro`。
