# Coding Agent Lab（mini-SWE-agent 复现入口）

本子项目以 [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) 2.x 为上游基线。上游是一个以 bash 为主要工具、可接本地或云端模型的极简 coding agent；本项目后续只在固定离线任务集上做可验证改动，不复制上游的 SWE-bench 宣称成绩。

## 当前复现状态

已在 Python 3.11 环境安装并导入 `mini-swe-agent==2.4.6`，版本检查：

```powershell
py -3.11 -c "from minisweagent import __version__; print(__version__)"
```

输出应为 `2.4.6`。交互式 `mini` CLI 需要终端输入和模型配置，因此不会在无 API key 的 smoke test 中伪造完整任务成绩。

## 下一步实验

- `baseline`：原始线性 agent loop。
- `optimized`：测试优先提示、命令失败分类、有限重试和停止条件。
- 任务集：10～20 个本地 Python 修复任务，每个任务带独立 pytest 验证器。
- 指标：任务通过率、平均工具调用数、失败恢复率、运行时间和 token/调用开销。

## 许可与边界

上游仓库采用 MIT License。本目录的新增评测脚本和任务 fixture 将单独标注，结果只代表本地固定任务集。
