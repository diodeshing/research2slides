# Research2Slides 协作说明

开始工作前先读取 `../../AGENTS.md`、`../../01_复利日志索引.md` 和本项目 `README.md`。

当前阶段以 `docs/architecture.md` 和各阶段 `docs/phase-*-implementation-report.md` 为准。不要跨阶段实现功能；每个阶段都必须同时提供 fixture、测试、example output 与验收标准。

常用验收命令：

```powershell
python -m pytest -q
python scripts/export_schemas.py --check
python C:\Users\10411\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\research-presentation
```
