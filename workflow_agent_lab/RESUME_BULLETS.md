# 简历项目描述

## 中文版

**Workflow Agent Lab｜面向企业退款流程的安全长程 Agent 与离线强化学习**

- 针对退款流程中“多步工具调用、工具故障和高风险提交”问题，设计可自动验证的 CRM/退款流程模拟环境，支持金额、账龄、故障类型和双故障压力测试。
- 实现 `safe_recovery` Agent：通过状态验证、有限重试、风险门控和人工审批，避免高金额/过期订单的危险提交；在 100 个双故障任务上成功率 100%、危险提交率 0%，固定顺序 baseline 成功率 45%、危险提交率 55%。
- 构建按 3:1 混合的低质量/安全离线轨迹数据，比较 Behavior Cloning、fitted Q 和 conservative fitted Q；Behavior Cloning 危险提交率 70%～80%，离线 Q 在 3 个独立 seed 上达到 100% 成功率、0 危险提交率。
- 将策略接入 FastAPI 本地业务服务，通过 HTTP reset/state/action 接口完成批量评测；提供一键复现实验、结构化轨迹、自动报告和 Selenium DOM 适配器。

## English version

**Workflow Agent Lab — Safe Long-Horizon Agent and Offline RL for Enterprise Refund Workflows**

- Built an auditable refund-workflow simulator with policy constraints, transient tool failures, human handoff, and automatic success or safety oracles.
- Implemented a state-verifying recovery agent with bounded retries and risk gating; achieved 100% success and 0% dangerous submissions on 100 two-failure episodes, versus 45% success and 55% dangerous submissions for a fixed-order baseline.
- Generated a 3:1 mixture of low-quality and safety-aware offline trajectories and compared behavior cloning, fitted Q iteration, and conservative fitted Q; behavior cloning inherited 70–80% dangerous submissions, while offline Q achieved 100% success and 0% dangerous submissions across three seeds.
- Exposed the environment through FastAPI `reset/state/action` endpoints and added reproducible batch evaluation, structured traces, and a DOM interaction adapter.

## 面试时的诚实边界

结果来自本地可复现实验环境，不应表述为真实企业线上收益，也不应冒充公开 benchmark 成绩。项目的价值在于问题定义、风险约束、失败恢复、离线数据偏差实验和端到端评测链路。
