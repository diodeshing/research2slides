# Phase 7 Real-World Validation Report

状态：Complete  
日期：2026-09-27  
范围：只完成 Phase 7；未开始 Phase 8/9。

## 目标与结论

Phase 1–6 已证明链路可运行；Phase 7 用三篇真实、公开、复杂度不同的 AI 论文验证它是否实际可用。结果是：三篇论文均完成 PDF + LaTeX 解析、Scientific Understanding、Evidence Graph、Storyline、Slide Spec、PPTX/PDF 渲染、讲稿、自动 QA 与逐页人工验收，共 26 页。P0 为 0，所有关键 P1 已修复。

| 论文 | 类型 | Slides | 自动 QA | 人工验收 |
|---|---|---:|---|---|
| Attention Is All You Need | 经典方法论文 | 8 | pass，0 issue | 8/8 通过 |
| Segment Anything | 视觉密集 CV | 9 | pass_with_warnings，1 coverage disclosure | 9/9 通过 |
| DeepSeek-V3 Technical Report | 现代复杂系统报告 | 9 | pass_with_warnings，1 coverage disclosure | 9/9 通过 |

官方来源：

- https://arxiv.org/abs/1706.03762
- https://arxiv.org/abs/2304.02643
- https://arxiv.org/abs/2412.19437

## Phase 7 交付物

每篇论文目录都包含 `input/`、`workspace/` 和最终 `output/`。最终 output 含：

- `presentation.pptx`
- `presentation.pdf`
- `presentation_outline.md`
- `speaker_notes.md`
- `quality_report.md`
- `scientific_understanding.md`
- `evidence_audit.md`
- `manual_slide_review.md`

横向报告：

- `examples/real-world/real_world_parse_report.md`
- `examples/real-world/qa_gap_analysis.md`

## 通用实现改进

1. 输入层：安全支持 arXiv TAR/TAR.GZ/TGZ source archive。
2. LaTeX parser：规范化标题与宏，支持 starred floats/equations。
3. Visual extraction：PDF Figure 栅格化、白边裁剪，同时保留 source provenance。
4. Renderer：清理复杂 LaTeX table/equation，处理 multirow/multicolumn、嵌套列格式、动态字号与 highlight 视图。
5. QA：真实论文揭示了“几何合法但语义不可读”的盲区，已通过人工复核闭环记录，并为后续视觉语义规则保留 P2 backlog。

## 证据与叙事完整性

- A 的 10 个、B 的 11 个、C 的 11 个 evidence nodes 均有可定位来源，合计 32 个高置信节点。
- 每页 Slide Spec 都引用已存在 evidence ID；未发现未知引用、无来源数字或来源错配。
- 三套 speaker notes 共 26/26 页字段完整，总预计讲述时长分别为 525、600、625 秒。
- B、C 未为了满足模板而生成独立 research-gap claim；自动 QA 的 coverage-gap warning 被有意保留。

## 最终判断

Research2Slides 已从 fixture 可运行状态进入“可处理真实科研论文并输出可讲述演示稿”的阶段。Phase 7 不代表已解决所有长尾 LaTeX 与视觉审美问题，但核心科学事实、证据追溯、叙事结构、PPTX/PDF 交付和人工审计闭环均成立。

## 最终验证

- Python：49 passed。
- TypeScript Renderer：15 passed。
- JSON Schema export check：通过。
- 三套 artifact validation：全部通过。
- 三套 PPTX：页数、speaker notes、所需 native table 与 A 的 editable equation 检查通过。
- 工作区治理测试：24 passed。
- `scripts/self_check.py --strict`：0 error，1 warning；warning 为工作区根 `.git` 缺少 `HEAD` 的既有环境问题，未擅自初始化或修改仓库。

Phase 8 可以开始，但应继续保持 GPT-5.6 Sol · High 用于架构与复杂实现；只有机械性测试、文档与重复 renderer 工作适合降到 Medium。
