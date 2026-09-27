# Phase 7 Real-World Examples

三篇论文均使用官方 arXiv PDF 与 LaTeX source 运行完整 Research2Slides pipeline。第三方论文的 PDF、LaTeX 原包和生成的 `output/`、`workspace/` 不进入公开仓库；仓库保留分析草稿、横向报告和阶段验收记录。

| 论文 | 官方来源 | 本地目录 |
|---|---|---|
| Attention Is All You Need | [arXiv:1706.03762](https://arxiv.org/abs/1706.03762) | `paper-a-attention/input/` |
| Segment Anything | [arXiv:2304.02643](https://arxiv.org/abs/2304.02643) | `paper-b-segment-anything/input/` |
| DeepSeek-V3 Technical Report | [arXiv:2412.19437](https://arxiv.org/abs/2412.19437) | `paper-c-deepseek-v3/input/` |

从上述官方页面下载 PDF 与 source archive，分别保存为对应目录中的 `paper.pdf` 和 `source.tar` 后，即可复现实验。最终 PPTX 和逐页人工审计会生成在各论文的本地 `output/` 目录中。

横向报告：[解析报告](real_world_parse_report.md) · [QA gap analysis](qa_gap_analysis.md) · [Phase 7 验收报告](../../docs/phase-7-real-world-validation-report.md)
