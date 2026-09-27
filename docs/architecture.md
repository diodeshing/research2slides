# Research2Slides Architecture

## 设计目标

系统把“内容理解”和“页面渲染”隔开。所有下游阶段只能读取经过 schema 校验的 artifact；Renderer 不得回读论文后自由补写内容。

```text
Sources -> Ingestion -> Parsing -> Evidence -> Planning -> Slide Spec -> Rendering -> QA
              |            |           |            |             |
       source_manifest  paper_structure evidence_graph presentation_plan slide_spec
                            + visual_manifest
```

## 稳定边界

| Artifact | Owner | 下游消费者 | 核心不变量 |
|---|---|---|---|
| `source_manifest.json` | ingestion | 所有阶段 | 输入路径、角色与 SHA-256 可核验 |
| `paper_structure.json` | parsing | Phase 2 | section/paragraph/figure/table/equation 均有稳定 ID |
| `visual_manifest.json` | assets | Phase 2/4/5 | 每个 asset 有来源、优先级、文件哈希和关联 section |
| `scientific_understanding.json` | understanding | Phase 3 | 12 个问题逐项映射 evidence ID；证据不足时显式标记 |
| `evidence_graph.json` | understanding | Phase 3/4/6 | claim 必须指向 source locator |
| `presentation_plan.json` | planning | Phase 4 | 信息单元按讲述逻辑而非 PDF 顺序组织 |
| `slide_spec.json` | slide authoring | renderer/QA | One Slide = One Main Idea；sources 可追溯 |

所有 JSON 都带 `schema_version`。不兼容变更提升 major version；新增可选字段提升 minor version。

## Phase 1 数据流

1. `SourceManifestBuilder` 对 PDF 与可选 LaTeX 输入计算哈希。
2. `PdfParser` 使用 `pypdf` 提取页级文本和元数据；未来可插入 MinerU、Docling 或 PyMuPDF adapter。
3. `LatexParser` 在隔离临时目录中安全解包 ZIP/TAR/TAR.GZ/TGZ，展开本地 `input/include`，解析结构和环境。
4. `merge_structures` 优先采用 LaTeX 的语义层级，保留 PDF 页级文本作为 page-grounded paragraph。
5. `AssetExtractor` 优先采用 LaTeX 原始 vector/raster；PDF Figure 的第一页通过 PyMuPDF 转成高分辨率 PNG 供 PowerPoint 嵌入，同时在 manifest 中保留原始 PDF 路径与 vector 来源标记，再补充未匹配的 PDF embedded image。
6. Pydantic 验证后用原子替换写出 JSON。输入指纹未变化且 artifact 有效时直接复用。

## Phase 2 数据流

1. `SourceCatalog` 将 paragraph、Figure、Table、Equation 转成带稳定 ID 的证据目录。
2. `UnderstandingProvider` 只产生 `analysis_draft.json` 形状的候选 claim；离线 JSON 与 Responses API 共用同一协议。
3. `EvidenceGraphBuilder` 在本地执行强校验：source ID 必须存在、excerpt 必须来自原始 artifact、实验/消融数字必须出现在引用来源中。
4. claim 与 relation 使用稳定 evidence ID 形成 `evidence_graph.json`。
5. 12 个科研理解问题分别映射 evidence ID；没有足够证据时输出 `insufficient_evidence`，不强迫模型填满答案。
6. 输入 artifact 与 provider 配置共同形成 fingerprint，允许安全复用 Phase 2 结果。

Provider 不是可信数据库。Structured Outputs 只约束候选数据形状；事实性由本地 evidence gate 再验证。

## Phase 3 数据流

1. 根据 `paper-reading` 或 `own-research` 选择独立 storyline prompt；两个模式不共享一份换词模板。
2. Provider 只返回带 evidence IDs 的 `storyline_draft`，不产生页面坐标或视觉布局。
3. 本地 planner 验证 evidence ID、数字来源、模式语态和关键顺序关系，再生成稳定 presentation unit ID。
4. `presentation_plan.full.json` 保存 Clarity First 完整叙事，并报告缺少证据支持的 narrative coverage gaps。
5. 若指定时间预算，deterministic compression 在保留 Problem、Core Idea、Method、Evidence、Limitations、Takeaway 等现有核心角色的前提下删减低优先级单元，写出 `presentation_plan.json`。
6. 完整计划和压缩计划使用同一 schema；下游 Phase 4 默认消费 `presentation_plan.json`。

Presentation unit 是信息单元和候选页面，不包含坐标、字号或最终 speaker notes。该边界属于 Phase 4。

## Phase 4 数据流

1. 根据 plan mode 选择独立 slide-authoring prompt；provider 只返回 `SlideSpecDraft`，不决定最终 ID、citation 或输入溯源信息。
2. `SlideSpecBuilder` 要求 draft slides 与选中 presentation units 一一对应，并锁定顺序、audience question、main claim、evidence IDs 与讲述时长。
3. title gate 拒绝泛化标题与不适合页面标题的标点；evidence gate 拒绝未知引用和 plan 之外的证据。
4. visual gate 分别校验 source asset、source table、source equation 与 conceptual diagram；source visual 除背景外不能跨页重复使用。
5. citation 由 evidence graph 的 source locator 确定性生成，provider 不能自由编写 citation。
6. `slide_spec.json` 保存结构化页面设计；`speaker_notes.md` 与 `presentation_outline.md` 是从同一 spec 确定性渲染的审阅视图。
7. 输入 artifact、provider 配置、mode 与 theme 共同形成 fingerprint；fingerprint 一致且 spec 合法时安全复用。

Phase 4 描述页面的语义与布局意图，不包含 PowerPoint 坐标。Phase 5 Renderer 负责把 layout intent 映射到主题模板与具体几何参数。

## Phase 5 数据流

1. Python CLI 调用项目级 TypeScript build，再把 workspace 和可选页面选择交给 Node Renderer。
2. Renderer 严格验证 `slide_spec.json` v1.1；spec 决定页面顺序、文字、视觉类型、引用、layout 与 notes。
3. `visual_manifest.json` 和 `paper_structure.json` 只解析 spec 已引用的 asset path、LaTeX table 与 equation，不参与内容规划，也不读取原始 PDF/LaTeX。
4. 统一 layout system 把八种 layout intent 映射到 16:9 geometry；两套主题只提供 typography、color、spacing 与 emphasis token。
5. reusable components 渲染 title、body、source visual、native table、editable equation text、conceptual diagram、takeaway、citation、folio 与 speaker notes。
6. PptxGenJS 写出 `.pptx` 后，sanitizer 删除 `[Content_Types].xml` 中指向不存在 slide master 的上游冗余声明；页面 XML、relationship、media 和 notes 不变。
7. spec、lookup artifact、theme、referenced assets、selection 和 renderer version 共同形成 fingerprint；匹配时复用完整 deck 或 partial review deck。

Phase 5 的 `rerender` 生成独立的 selected-slide review deck，不在原 PPTX 中原位替换页面。原位 repair 与自动视觉判断属于 Phase 6。

## Phase 5.1 语言边界

```text
Scientific Understanding（语言中立语义）
  -> Presentation Plan（中文叙事与术语首次引入）
  -> Slide Spec（最终中文页面文案与中文讲稿）
  -> Renderer（排版、字体选择与渲染，不翻译）
```

1. 默认语言配置为 `zh_cn_bilingual_terms`，其 typed config 明确 `zh-CN`、双语术语、源视觉语言保留、通用标签翻译和中文 speaker notes。
2. Planner 与 Slide Spec Builder 对标题、section、question、claim、正文、takeaway 和 notes 执行 CJK presence gate，阻止 English-first artifact 进入 Renderer。
3. Prompt 直接要求中文科研表达，不存在 `English slide -> translation() -> Chinese slide` 后处理。
4. 原始 Figure 作为 evidence 原样嵌入；外部 annotation 使用中文。Equation 保留数学符号，解释使用中文。
5. editable table 的通用表头由 Slide Spec 中的 `table_column_labels` 决定；Renderer 只应用已声明标签，模型名、指标名和数值保持源数据。
6. theme 与 language profile 解耦。主题提供字体候选顺序，Renderer 在 Windows 上选择已安装候选，并允许环境变量覆盖。

Phase 5.1 本身不包含自动视觉判断或修复循环；这些能力由后续 Phase 6 提供。

## Phase 6 数据流

```text
validated artifacts + presentation.pptx
  -> factual / storyline / presentation checks
  -> PPTX -> PDF -> per-slide PNG
  -> OOXML geometry + preview checks
  -> quality_report.json / quality_report.md
  -> evidence-preserving safe repair
  -> targeted review render + full rerender + reinspection
```

1. QA 只消费已验证的 Phase 1–5 artifacts，不回读原始论文并自由产生新 claim。
2. factual QA 核对 paper ID、evidence/citation/source locator、页面数字、源视觉哈希和实验视觉身份。
3. storyline QA 再次锁定 Plan → Spec 的 unit 顺序、question、main claim 与 evidence IDs，并报告 coverage gap、重复信息或叙事倒序。
4. visual QA 解析 OOXML 检查页数、16:9、notes、文本边界、重叠、字体和 native table；逐页 PNG 用于检查渲染产物是否完整且分辨率合格。
5. presentation QA 核对 notes、讲述时间、transition 和页面核心信息的一致性。
6. 每个 finding 使用内容派生的稳定 ID，severity 决定 `pass`、`pass_with_warnings` 或 `fail`。
7. 自动 repair 前后计算 evidence signature。签名覆盖 evidence IDs、citations 和视觉 source refs；任何变化都立即拒绝。
8. 当前 deterministic repair 只处理标题末尾标点。语义改写、数值、证据和视觉来源修复必须人工批准。
9. 受影响页面先生成独立 targeted review deck；随后重建完整 PPTX、PDF、PNG 并执行同一套复检。
10. PDF backend 支持 Windows PowerPoint-compatible COM 与 LibreOffice；PNG 支持 PyMuPDF 和 Poppler fallback。

## 安全与失败语义

- ZIP/TAR entry 出现绝对路径、`..` 路径穿越、symlink、hardlink 或特殊设备条目时拒绝处理。
- 不执行 LaTeX、不运行 shell、不下载远程资源。
- 输入缺失、格式不支持、schema 不合法使用可读异常并返回非零退出码。
- `--force` 只覆盖指定 workspace 下可重建 artifact，不删除其他文件。

## QA 边界

- 自动规则不能证明复杂科研 claim 的语义蕴含，也不能代替人工逐页审美和真实讲述检查。
- `quality_report` 明确保存这些限制并始终要求最终人工复核。
- QA 发现证据错误时只报告，不得静默改写 source evidence。

## Phase 7 真实论文验证

Phase 7 不增加新的语义生成阶段，而是以三种不同复杂度的公开论文验证既有边界：经典方法论文、视觉密集 CV 论文与现代复杂系统技术报告。每篇论文固定保存官方 PDF 与 LaTeX source、所有中间 artifact、PPTX/PDF、讲稿、质量报告、证据审计和逐页人工复核。

真实输入暴露出的通用缺口只能通过可复用修复进入主链路，例如 TAR source、安全解包、starred LaTeX 环境、PDF Figure 栅格化与裁边、复杂表格列格式解析。仅对单页有效的内容调整保留在该论文的 Slide Spec draft，不改变 parser 或 renderer 的通用语义。

Phase 7 的完成条件是：三条流水线重跑成功、每页最终 PNG 全尺寸人工检查、P0 清零、关键 P1 修复、自动 QA false negative/true positive 记录完整，并且 Phase 8 未被提前实现。

## Phase 8 一键编排与交付

```text
PDF + optional LaTeX + provider inputs
  -> parse -> understand -> plan -> spec -> render -> qa -> package
  -> build_checkpoint.json
  -> delivery/
```

1. `build` 只编排 Phase 1–7 已存在的公共入口，不复制 parser、provider、renderer 或 QA 逻辑。
2. 输入文件哈希、provider cache key 与构建配置共同形成 fingerprint；fingerprint 不变时可以复用已完成步骤。
3. 每一步先写入 `running`，成功后写入 `completed`，异常写入 `failed`；checkpoint 使用原子替换，进程中断后仍可判断最后可靠边界。
4. 默认自动跳过已完成且输出存在的步骤；`--resume-from` 显式使指定步骤及其下游重新执行，`--force` 使整条流水线重建。
5. QA 的 `fail` 是硬门禁，不能进入 package；`pass_with_warnings` 可交付，但警告和人工复核要求必须随交付物保留。
6. package 只复制稳定交付面：PPTX、PDF、speaker notes、outline、质量报告和 checkpoint，不把中间缓存伪装成最终交付。

Phase 8 的 DeepSeek-V3 样例验证了失败 checkpoint、自动续跑、显式 resume、Windows PowerPoint 渲染、9 页逐页人工检查和交付目录完整性。

## Phase 9 Semantic QA 2.0

```text
Slide Spec + Presentation Plan + Evidence Graph
  -> structured semantic evaluator
  -> semantic_qa.json
  -> local identity / scope / ordering gates
  -> factual + storyline findings
  -> Quality Report
```

1. Evaluator 只接收页面 claim、正文、takeaway、本页 evidence node/source excerpt、叙事角色和 Evidence Graph edges，不接收开放网络信息。
2. 每页必须在原顺序中返回一个结构化 evaluation，并引用本页已有 evidence ID 的非空子集；未知页面、跨页借证或缺页会使 Semantic QA 本身失败。
3. Claim-evidence 检查区分 `entailed`、`partially_supported`、`unsupported` 与 `insufficient_evidence`。Unsupported 是事实层 error；partial/insufficient 是需人工复核的 warning。
4. Claim-strength 检查专门识别因果、统计显著性、SOTA、绝对化和普遍性措辞是否强于证据；overstated 是 error。
5. Storyline dependency 记录理解当前页所必需的前置概念及其页面；缺少前置页或前置页出现在当前页之后时产生 warning。
6. Semantic evaluator 可使用 Responses API 或离线 JSON draft。结果按输入和 provider fingerprint 缓存，并随交付包保存。
7. Semantic findings 的 repairability 固定为 `none`。系统不允许 evaluator 自动缩写 claim、替换 evidence、调整数字或重排故事线。

Phase 9 仍保留人工抽查边界：结构化模型判断提高覆盖率，但不能把第二个模型的判断当作论文事实数据库。

## Phase 10 Semantic QA Benchmark

Phase 10 不改变生产 QA 判定，只增加可重复的校准层。通用 runner 从配置读取 workspace、人工审核 draft 和 mutation cases；核心代码不包含论文标题、slide ID 或 evidence ID 特判。

基准分别统计人工基准上的已有 finding，以及对 unsupported、partial、overstated 和 dependency-order 注入错误的命中情况。它验证本地 gate 与严重度映射，不宣称代表远程模型 evaluator 的真实准确率；后者仍需要冻结模型版本并进行独立盲评。

## Phase 11 Release Boundary

Python wheel 包含 Python pipeline、CLI、Schema 代码与 8 个 prompt assets。`version` 检查安装版本，`doctor` 分别报告 Python core、prompt assets、Node/npm 和 Renderer 源码可用性。

TypeScript Renderer 当前不嵌入 wheel：其运行依赖 `package.json`、`renderer/`、Node/npm 与 npm dependencies。源码 checkout 可直接使用；wheel 用户必须通过 `RESEARCH2SLIDES_RENDERER_ROOT` 指向完成 `npm ci` 的项目目录。该边界由 doctor 明确报告，避免 wheel 安装成功被误解为完整渲染环境已经就绪。

## Phase 12 Offline Local Bundle

Windows 本地完整包把 Python wheel、全部锁定的 runtime wheels、Renderer 源码与编译产物、主题、`node_modules`、PowerShell launcher 和离线 fixture 放入一个 ZIP。安装脚本使用 `pip --no-index`，运行脚本自动设置 `RESEARCH2SLIDES_RENDERER_ROOT`。

验证器先防止 ZIP path traversal，再逐文件核对 `SHA256SUMS.txt`，随后在临时目录创建虚拟环境、离线安装，并运行 parse → understand → plan → spec → render → Semantic QA → package。PDF 导出仍依赖目标机器上的 PowerPoint 或 LibreOffice，因此离线 smoke test使用 `--no-render-qa`。
