# Phase 12 Local Bundle

- `output/research2slides-0.2.0-windows-local.zip`：Windows 离线完整包。
- `output/local_bundle_manifest.json`：构建信息与 ZIP SHA-256。
- `output/local_bundle_validation.json`：解压、checksum、离线安装及端到端验证结果。
- `wheel_cache/`：构建 ZIP 使用的锁定 Python wheels。

目标机器仍需预装 Python 3.11+ 与 Node.js 20+，但安装 Research2Slides 与其 Python/Node 包依赖时不需要联网。
