# Phase 10 — Semantic QA Benchmark

状态：Complete  
日期：2026-09-27

## 结果

| 指标 | 结果 |
|---|---:|
| 真实论文 | 3 |
| 人工审核页面 | 26 |
| 人工基准上的 Semantic QA finding | 0 |
| 注入错误 | 12 |
| 正确命中 | 12/12 |
| 额外 finding | 0 |

覆盖 Attention Is All You Need、Segment Anything 和 DeepSeek-V3。每篇分别注入 unsupported claim、partial support、overstated claim 与 prerequisite 倒置。

## 实现

- 通用配置：`examples/phase10/benchmark.json`
- Runner：`scripts/run_semantic_benchmark.py`
- 机器结果：`examples/phase10/output/semantic_benchmark.json`
- 阅读报告：`examples/phase10/output/semantic_benchmark.md`
- 回归测试：`tests/test_semantic_benchmark.py`

## 边界

100% 是确定性 gate 对已定义注入案例的检测率，不是远程 LLM evaluator 的准确率。下一步若继续，应冻结 evaluator 模型与 prompt，对独立双人标注集做盲评，计算 agreement、precision 和 recall。

最终回归：Python 60 passed，Renderer 15 passed，工作区治理测试 24 passed，Schema 检查通过。严格自检为 0 error、1 个既有的根 `.git` 缺少 `HEAD` 警告。
