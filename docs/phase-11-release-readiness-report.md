# Phase 11 — Release Readiness

状态：Complete  
版本：0.2.0  
日期：2026-09-27

## 已完成

- Python、package 与 Renderer 版本同步为 `0.2.0`。
- 新增 MIT `LICENSE` 与 `CHANGELOG.md`。
- 8 个模型 prompt 随 wheel 安装。
- 新增 `research2slides version` 和 `research2slides doctor`。
- Renderer 缺少源码资产时提供明确错误，并支持 `RESEARCH2SLIDES_RENDERER_ROOT`。
- 构建 wheel 后在隔离虚拟环境安装，验证版本、prompt assets、doctor 与 PDF/LaTeX parse。

## 验收结果

- Wheel：`research2slides-0.2.0-py3-none-any.whl`
- Prompt assets：8/8
- Installed core：ready
- Parse smoke：2 页 fixture 成功
- Installed renderer：not ready，符合 wheel 的已声明边界
- 未执行 PyPI/npm 发布
- Python：64 passed
- Renderer：15 passed
- 工作区治理：24 passed
- 严格自检：0 error、1 个既有的根 `.git` 缺少 `HEAD` 警告

发布前仍需用户决定包仓库、命名所有权、版本标签与 Renderer 分发方式。
