# Workflow Agent Lab

一个面向企业退款流程的安全长程 Agent 实验台。项目不依赖云端模型或真实业务数据，使用本地可验证环境研究一个明确问题：**当业务流程包含策略约束、页面/工具故障和高风险提交时，Agent 能否完成任务并避免错误提交？**

## 问题定义

每个任务包含客户、订单、退款原因和金额。Agent 需要查询订单、检查退款政策、填写退款单，并在金额超阈值或订单过期时转人工审批。环境会随机注入一次工具失败或状态不一致，考察 Agent 是否能验证状态、重试和恢复。

当前实现提供两个可对照策略：

- `naive`：固定顺序执行，遇到错误直接失败；
- `safe_recovery`：显式维护任务状态，在每个关键动作后验证，按风险规则转人工，并对可恢复错误有限重试。

## 运行

```powershell
py -3.11 evaluate.py --episodes 100 --seeds 7 11 21
```

输出 `results/metrics.json`，包含任务成功率、恢复率、危险提交率、人工介入率、平均步数和失败类型分布。

运行一个可展示的高风险退款演示：

```powershell
py -3.11 demo.py --amount 900 --failure find_order
```

终端会输出结构化动作轨迹，展示工具失败、重试和人工审批，而不是只打印一个最终成功/失败标签。

测试连续故障场景：

```powershell
py -3.11 robustness.py --episodes 100 --seed 101
```

该评测每个任务注入两个独立工具故障，用于验证恢复策略是否只对单一故障过拟合。

启动本地业务 HTTP 页面并运行 Agent：

```powershell
py -3.11 -m uvicorn web_app:app --host 127.0.0.1 --port 8765
# 另开一个终端
py -3.11 http_agent.py --url http://127.0.0.1:8765
```

`web_app.py` 提供页面、状态读取、动作提交和重置接口；`http_agent.py` 通过 HTTP 获取状态并提交动作，因此后续可以把 requests 替换为 Playwright、BrowserGym 或多模态模型，而不改变业务环境和安全评测逻辑。

通过 HTTP 边界批量评测不同金额、账龄和故障：

```powershell
py -3.11 http_eval.py --url http://127.0.0.1:8765 --episodes 30
```

该脚本不会直接访问 Python 环境对象，所有状态和动作都经过 HTTP 接口。

如果本机安装了 Microsoft Edge 和 Selenium，还可以通过真实 DOM 运行：

```powershell
py -3.11 -m uvicorn web_app:app --host 127.0.0.1 --port 8765
# 另开终端
py -3.11 selenium_agent.py --url http://127.0.0.1:8765/
```

该适配器会读取页面上的状态 JSON，根据安全策略定位按钮并点击；它不是直接调用环境对象。

如果 Selenium Manager 无法下载驱动，HTTP 适配器仍可直接运行；浏览器适配器只依赖本地 Edge 和匹配版本的 `msedgedriver`。

一键运行主要实验并生成总报告：

```powershell
py -3.11 run_all.py --episodes 30
```

该命令会依次运行本地 baseline、混合数据离线 RL、双故障压力测试和 HTTP 集成评测，并在结束时自动关闭临时 HTTP 服务，输出 `results/summary.json`。

导出安全 Agent 的轨迹并训练离线动作策略：

```powershell
py -3.11 offline_rl.py --episodes 100 --seeds 7 11 21
```

该命令生成 `results/trajectories.jsonl` 和 `results/offline_rl.json`。数据由安全策略和按 3:1 oversample 的低质量固定顺序策略混合而成，报告会比较行为克隆、无保守惩罚 fitted Q 和 conservative fitted Q 三组结果。当前使用可审计的 tabular 方法，是后续神经 action scorer/offline RL 的最小闭环，不依赖 GPU 或远程模型。

## 研究问题与后续强化学习扩展

1. 状态验证是否降低长流程错误的累积？
2. 风险门控是否能在不显著降低完成率的情况下减少危险提交？
3. 将轨迹中的动作选择记录为离线数据后，可训练一个 action scorer 或 offline RL 策略，优化“成功率—步数—人工介入”多目标奖励。

第一版刻意使用确定性的业务模拟器和规则策略，保证评测链路可审计；后续再接入本地 LLM/VLM 或 BrowserGym，而不是一开始把问题隐藏在不可复现的 API 调用中。

## 许可与边界

本目录为新增实验代码，不包含真实客户数据。它可以作为 Agent 项目的核心评测环境，也可以作为后续浏览器操作 Agent 的后端 oracle。
