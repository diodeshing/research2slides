# Phase 7 Real-World Parse Report

日期：2026-09-27  
输入：三篇公开 AI 论文的官方 arXiv PDF 与 LaTeX source archive。所有测试都以冻结到本地的输入运行，不依赖在线内容在执行时保持不变。

| 论文 | 角色 | 官方来源 | 页 | Sections | Paragraphs | Figures | Tables | Equations | Visual assets |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Attention Is All You Need | A：经典、结构清晰 | https://arxiv.org/abs/1706.03762 | 15 | 36 | 907 | 6 | 7 | 11 | 9 |
| Segment Anything | B：视觉密集 CV | https://arxiv.org/abs/2304.02643 | 30 | 117 | 3029 | 20 | 9 | 0 | 207 |
| DeepSeek-V3 Technical Report | C：现代复杂系统报告 | https://arxiv.org/abs/2412.19437 | 53 | 86 | 2368 | 15 | 9 | 15 | 38 |

## 解析结论

- PDF 与 arXiv TAR source 均可通过统一 `ingest` 入口处理；TAR/TAR.GZ/TGZ 解包拒绝路径穿越、符号链接、硬链接与特殊文件。
- LaTeX parser 已覆盖 starred figure/table/equation/align 环境，避免真实论文中的 `figure*`、`table*` 静默丢失。
- PDF Figure 在写入 PPTX 前栅格化并裁掉纯白边距，同时在 manifest 中保留原 PDF source 与 `latex_vector` provenance。
- Segment Anything 解析到 0 个独立 display equation，与源稿结构相符；没有为了模板完整性伪造公式。
- 三篇论文合计解析 71 个 Figure/Table/Equation 结构节点、254 个视觉资产候选；最终演示稿只选择与 claim 直接相关的视觉。

## 人工抽查

- A：Figure 1 架构图、Table 3 WMT 结果、Equation 1 Attention 公式。
- B：SAM overview、三阶段数据引擎、SA-1B 规模图、零样本结果、消融与地理代表性图；无独立 equation。
- C：基础架构、MTP、FP8、NIAH、训练成本表、MTP 消融表，以及 MLA 前 3 个 display equations。

## 已知解析边界

- P2：论文自定义宏尚未在所有 caption/text 中全局展开，少数解析 caption 会缺失 `SAM`、`SA-1B` 或 `DeepSeek-V3` 字样。最终 Slide Spec 通过已核对的证据与原图补足语义，但底层 parser 仍应在后续阶段实现受控宏展开。
- P2：同一源图被多处引用时 manifest 可能出现重复 asset 记录；不影响 provenance 或最终选图，但可进一步去重。
