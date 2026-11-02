# Agent-pro 项目选择与复现路线

本仓库不再围绕 CCQMIX 或 Agent 安全评测展开，改为两个可独立写进简历的开源项目复现：一个 Agent，一个强化学习。

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
