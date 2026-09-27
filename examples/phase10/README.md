# Phase 10 Semantic QA Benchmark

运行：

```powershell
python scripts\run_semantic_benchmark.py examples\phase10\benchmark.json --output examples\phase10\output
```

当前基准覆盖三篇论文、26 页人工审核 draft 和 12 个注入错误。输出中的 100% detection recall 只表示本地 QA gate 命中这些已定义案例，不代表远程 evaluator 模型准确率。
