# Offline RL Lab（CleanRL + Minari 路线）

本项目选择 [CleanRL](https://github.com/vwxyzjn/cleanrl) 的易审计实现风格和 [Minari](https://github.com/Farama-Foundation/Minari) 的离线数据接口，先构建一个 CPU 可复现的稀疏奖励 ChainEnv 离线 RL 基线。数据由固定 seed 生成，避免依赖外部下载服务。

## 当前实验

- `BC`：行为克隆，只拟合离线数据中的动作。
- `CQL`：离散动作 Conservative Q-Learning，加入 `logsumexp(Q) - Q(a_data)` 保守项，抑制 OOD action 的过估计。
- 评估：独立 seed 的 ChainEnv episode 平均回报；离线数据刻意包含大量“停留在起点”的低质量轨迹，用于检验算法是否能利用少量高回报轨迹。

运行：

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 train_offline.py --episodes 80 --seeds 7 11 21
```

结果写入 `results/metrics.json`。后续将增加 advantage-weighted BC、数据质量消融和 Minari 数据集导出。

当前三 seed 结果：BC 平均回报 `-0.20`，CQL 平均回报 `0.96`，提升 `+1.16`。这是一个小型可复现实验，不等同于 MuJoCo 或 D4RL 论文结果；它的价值在于完整展示离线数据偏差、保守 Q 学习和独立评估链路。
