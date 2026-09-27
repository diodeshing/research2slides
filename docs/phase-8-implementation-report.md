# Phase 8 实现与验收报告

## 目标

把 Phase 1–7 的独立命令串成可恢复的一键流水线，并对最终交付边界负责。Phase 8 不新增内容生成逻辑，不改变 `paper_structure -> evidence_graph -> presentation_plan -> slide_spec` 的所有权。

## 实现

- 新增 `research2slides build`，按 parse、understand、plan、spec、render、qa、package 执行。
- 新增 `build_checkpoint.json`，记录 fingerprint、配置、每步状态、时间和输出摘要。
- 支持自动续跑、`--resume-from` 显式续跑和 `--force` 全量重建。
- QA 失败时停止打包；通过或带警告通过时生成 `delivery` 目录。
- 交付目录包含 PPTX、PDF、speaker notes、outline、JSON/Markdown 质量报告和 checkpoint。
- 新增 orchestration 单元测试与 CLI 离线集成测试，覆盖失败持久化、跳步续跑和交付打包。

## 真实样例

样例目录：`examples/phase8/deepseek-v3-refined/workspace`。

- 论文：DeepSeek-V3 Technical Report
- 模式：paper-reading
- 语言：中文主导、双语技术术语
- 主题：group-meeting
- 页数：9
- 渲染后端：Windows PowerPoint-compatible COM
- QA：`pass_with_warnings`
- 告警：1 个已声明的 storyline coverage gap；无 factual、visual 或 presentation 错误
- 人工验收：9 页最终 PNG 均以原始分辨率检查，无阻塞问题

## 恢复性验证

真实构建第一次在 spec 阶段暴露不支持的 native-table 布局，修正后第二次在 QA 阶段捕获无证据支撑的 `2K` 页面数字。两次失败均写入 checkpoint；最终从 render 显式续跑，复用已经完成的上游 artifact，并完成 QA 与 package。这说明 checkpoint 不只是成功日志，也能保留可操作的失败边界。

## 完成条件

- 一键 build 能从真实 PDF/LaTeX 和离线 provider draft 生成交付目录。
- 构建失败不会把未通过 QA 的演示稿标记为完成。
- 中断或失败后可以复用合法上游结果。
- 最终 PPTX、PDF、讲稿、outline、质量报告和 checkpoint 同步交付。
- 自动检查与 9 页逐页人工验收均完成。

## 最终验证

- Python：51 passed
- Renderer：15 passed
- Schema export check：通过
- Phase 8 artifact validation：通过
- 9 页 PPTX package、speaker notes 与 native table：通过
- 相同参数二次执行：1.5 秒完成，复用已完成 checkpoint
- 工作区治理测试：24 passed
- 严格工作区自检：0 error、1 warning；警告为根 `.git` 缺少 `HEAD` 的既有工作区问题，与本项目无关
