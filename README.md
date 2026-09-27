# Research2Slides

Research2Slides 是一个 **Research Presentation Agent**：把科研材料转化为可讲清楚、证据可追溯的学术汇报，而不是把论文段落机械搬进 PowerPoint。

当前状态：**Phase 1–12 已实现**。除 `0.2.0` wheel 外，现已提供约 42.5 MB 的 Windows 本地完整包，包含离线 Python wheels、Renderer、Node dependencies、安装脚本和端到端验证样例。

## 核心链路

```text
PDF + LaTeX
  -> paper_structure.json
  -> visual_manifest.json
  -> evidence_graph.json          (Phase 2)
  -> presentation_plan.json       (Phase 3)
  -> slide_spec.json              (Phase 4)
  -> presentation.pptx            (Phase 5)
  -> QA / repair loop              (Phase 6)
  -> real-world validation         (Phase 7)
  -> build / resume / delivery      (Phase 8)
  -> semantic QA 2.0                (Phase 9)
  -> semantic benchmark             (Phase 10)
  -> release readiness              (Phase 11)
  -> offline local bundle           (Phase 12)
```

详细边界见 [architecture.md](docs/architecture.md)，最新验收记录见 [Phase 9](docs/phase-9-implementation-report.md) 与 [Phase 10](docs/phase-10-semantic-benchmark-report.md)。早期阶段报告保留在 `docs/phase-*-implementation-report.md`。

## Phase 1 能力

- 解析 PDF 元数据、页码、文本段落和粗粒度 section hierarchy。
- 安全解包 LaTeX ZIP/TAR/TAR.GZ/TGZ，解析 `section/subsection`、figure、table、equation、caption、label、ref 与 `includegraphics`。
- 按 `LaTeX vector -> LaTeX raster -> PDF embedded image` 优先级生成视觉资产清单。
- 生成带 SHA-256 的 `source_manifest.json`，已存在且输入未变时复用有效 artifact。
- 用 Pydantic 和 checked-in JSON Schema 双重约束中间接口。
- 提供两套离线集成 fixture：Attention Is All You Need 与 An Image is Worth 16x16 Words。fixture 只保留测试所需的原创最小文本/图形，并链接公开论文来源，不复制论文全文。

## Phase 2 能力

- 将论文证据目录交给可替换的 understanding provider，而不是把系统锁死在单一模型厂商。
- 支持 OpenAI Responses API Structured Outputs；默认 `gpt-5.6-sol` + `high`，模型、reasoning effort、base URL 和 API key 环境变量均可配置。
- 支持离线 `analysis_draft.json` provider，用于可复现测试、人工审阅和外部模型接入。
- 输出 `scientific_understanding.json`，对 12 个科研理解问题逐项标记 `supported` 或 `insufficient_evidence`。
- 输出 `evidence_graph.json`；每个节点包含稳定 ID、claim、confidence 与 paragraph/Figure/Table/Equation locator。
- 拒绝未知 source ID、非原文 excerpt、越界 relation，以及来源中不存在的实验/消融数字。

## Phase 3 能力

- `paper-reading` 与 `own-research` 使用两套独立 prompt、叙事语态和覆盖要求。
- 将 evidence nodes 重构成顺序明确的 presentation units，而不是照搬论文 section。
- 每个 unit 固定一个 audience question、一个 main claim、证据 ID、重要度、讲述时长、设计理由与 transition intent。
- 本地检查未知 evidence ID、无证据数字、错误模式语态和明显的叙事倒序。
- 默认 Clarity First：先生成 `presentation_plan.full.json`，不预设页数。
- 可用时间预算压缩为 `presentation_plan.json`；压缩只删减低优先级单元，保留完整计划和核心叙事角色。

## Phase 4 能力

- 把每个选中的 presentation unit 一对一转换为完整 slide，保持顺序、问题、main claim、evidence ID 与讲述时间一致。
- `paper-reading` 与 `own-research` 使用独立的 slide-authoring prompt；支持 `group-meeting` 与 `conference-minimal` 主题意图。
- 每页包含 claim-based title、technical title、body、visual treatment、annotations、takeaway、citation、layout intent 与完整 speaker notes。
- source figure、table、equation 和 conceptual diagram 均有本地引用校验；实验视觉不允许被伪造，普通 source visual 不允许跨页重复使用。
- speaker notes 固定包含 Purpose、Main Message、Speaking Script、Visual Guidance、Transition 与 Estimated Time，并输出便于审阅的 Markdown。
- 拒绝泛化标题、标题中的禁用标点、证据漂移、未知视觉引用、讲稿时间漂移以及页面与 plan 不一致。
- 通过输入 fingerprint 安全复用 `slide_spec.json`，同时重新生成缺失的 notes 或 outline。

## Phase 5 能力

- TypeScript + PptxGenJS Renderer 以 `slide_spec.json` 作为唯一内容决策来源；只用 `visual_manifest.json` 与 `paper_structure.json` 解析已经选定的 asset/table/equation 引用。
- 两套主题 token：`conference-minimal` 与 `group-meeting`，共享统一的 16:9 layout geometry 和 reusable components。
- 支持八种 layout intent，以及 text、原始 SVG/raster、editable table、editable equation text、conceptual diagram、annotation、caption、citation、takeaway、slide number 与 PowerPoint speaker notes。
- source asset 使用 contain 布局保持比例；LaTeX 简单表格转换为 native PowerPoint table；公式保留为可编辑文本。
- `render` 生成完整 deck；`rerender --slides` 生成选中页面的 review deck。
- render fingerprint 覆盖 spec、lookup artifacts、theme、已引用资产与页面选择；输入未变时安全复用输出。
- 输出后执行确定性的 OOXML content-type 清理，以修复 PptxGenJS 4.0.x 的无效 slide-master 声明；不改页面、媒体、关系或 notes。

## Phase 5.1 语言模式

- 默认 `language_profile = "zh_cn_bilingual_terms"`：中文承担主要讲解，技术术语首次出现时保留英文名称，后续使用中文、缩写或通行英文名。
- `presentation_plan.json` 与 `slide_spec.json` 明确保存 `presentation.language`、`terminology_mode`、源视觉语言保留、通用标签翻译和中文讲稿开关。
- Scientific Understanding 保持语言中立；Presentation Plan 直接组织中文叙事；Slide Spec 直接产生可渲染中文文案。Renderer 不执行翻译。
- 原始 Figure 内部英文、Equation、模型/Dataset/Metric 名称不变；可编辑表格可由 `table_column_labels` 中文化通用表头。
- 两套主题共享中文字体候选顺序：Microsoft YaHei、Noto Sans CJK SC、Source Han Sans SC、Arial。可用 `RESEARCH2SLIDES_FONT_FAMILY` 显式指定目标环境字体。
- 中文 title、body、annotation、takeaway 与 speaker notes 具有本地验证；纯英文页面会在 Slide Spec 构建阶段被拒绝。

## Phase 6 QA 与修复循环

- `qa` 读取已经验证的 `slide_spec.json`、`presentation_plan.json`、`evidence_graph.json`、`paper_structure.json` 和 `visual_manifest.json`，不重新解释原论文。
- factual QA 核对 evidence/citation/source locator、页面数字、源视觉哈希，以及实验结果页是否错误使用生成式示意图。
- storyline QA 核对 Problem → Method → Evidence → Conclusion、Plan/Spec 顺序与锁定字段、重复 main claim 和显式 coverage gap。
- visual QA 检查 PPTX 页数、16:9 画布、notes part、越界、重叠、过小字体、native table，并验证逐页 PNG 的数量、分辨率和宽高比。
- presentation QA 核对 speaker notes 与页面 claim/purpose、讲述时间、transition 和标题格式。
- 默认执行 `PPTX → PDF → PNG`。Windows 使用 PowerPoint-compatible COM，其他环境可使用 LibreOffice；PNG 优先用 PyMuPDF，缺失时自动回退到 Poppler `pdftoppm`。
- 自动 repair 只处理不改变语义的低风险格式问题，并用 evidence signature 锁定 evidence IDs、citations 与视觉 source refs。数值、证据或源视觉变更一律留给人工批准。
- 每轮修复先生成受影响页面的 review deck，再重建完整 deck 并运行同一组检查。
- 输出 `quality_report.json`、便于人工阅读的 `quality_report.md`、最终 PDF 和逐页 PNG。

## 环境与安装

- Python 3.11+
- Node.js 20+（Phase 5 才需要）

```powershell
cd D:\workspace_codex\projects\research2slides
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pip install -e .
npm ci
```

检查当前安装：

```powershell
research2slides version
research2slides doctor --require-renderer
```

Python wheel 包含 Phase 1–4、Semantic QA 和所有 prompt assets。PptxGenJS Renderer 仍需要源码 checkout 中的 `package.json`、`renderer/` 和 `node_modules`；从 wheel 调用渲染时，可设置：

```powershell
$env:RESEARCH2SLIDES_RENDERER_ROOT = "D:\path\to\research2slides"
```

本地 release 验收：

```powershell
python scripts\release_check.py --output examples\phase11\output
```

构建与验证 Windows 离线完整包：

```powershell
python scripts\build_local_bundle.py `
  --output examples\phase12\output `
  --wheel-cache examples\phase12\wheel_cache
python scripts\validate_local_bundle.py `
  examples\phase12\output\research2slides-0.2.0-windows-local.zip `
  --report examples\phase12\output\local_bundle_validation.json
```

生成 ZIP 后，目标机器只需预装 Python 3.11+ 与 Node.js 20+；包内安装过程不访问网络。

`PyMuPDF` 用于把 LaTeX 中的 PDF Figure 栅格化为可嵌入 PowerPoint 的高分辨率 PNG，也用于 Phase 6 逐页预览；正文文本仍由 `pypdf` 提取。

## 使用

```powershell
research2slides parse tests\fixtures\attention_is_all_you_need\paper.pdf `
  --latex tests\fixtures\attention_is_all_you_need\source.zip `
  --workspace workspace\attention
```

也可以不安装 entry point：

```powershell
python -m research2slides.cli.app parse tests\fixtures\vision_transformer\paper.pdf `
  --latex tests\fixtures\vision_transformer\source.zip `
  --workspace workspace\vit
```

Phase 2 离线验收：

```powershell
python -m research2slides.cli.app understand workspace\vit `
  --draft tests\fixtures\vision_transformer\analysis_draft.json
```

真实模型分析（需要提前设置 `OPENAI_API_KEY`）：

```powershell
python -m research2slides.cli.app understand workspace\vit `
  --model gpt-5.6-sol `
  --reasoning-effort high
```

API key 只从指定环境变量读取，不写入配置、日志或 artifact。OpenAI-compatible Responses endpoint 可通过 `--base-url` 与 `--api-key-env` 切换。

Phase 3 离线规划：

```powershell
python -m research2slides.cli.app plan workspace\vit `
  --mode paper-reading `
  --language-profile zh_cn_bilingual_terms `
  --draft tests\fixtures\vision_transformer\storyline_paper_reading.json
```

Phase 4 离线页面设计与讲稿生成：

```powershell
python -m research2slides.cli.app spec examples\phase4\paper-reading `
  --draft tests\fixtures\attention_is_all_you_need\slide_spec_paper_reading.json `
  --theme group-meeting
```

真实模型生成与 Phase 2、3 使用相同的 `--model`、`--reasoning-effort`、`--base-url` 和 `--api-key-env` 参数。默认主题按模式选择：`paper-reading` 使用 `group-meeting`，`own-research` 使用 `conference-minimal`。

Phase 5 完整渲染：

```powershell
python -m research2slides.cli.app render examples\phase5\paper-reading
```

只重渲染原始第 2、4 页到独立 review deck：

```powershell
python -m research2slides.cli.app rerender examples\phase5\paper-reading --slides 2,4
```

Phase 6 完整 QA、预览与安全修复：

```powershell
python -m research2slides.cli.app qa examples\phase5\paper-reading
```

只运行结构、事实与讲稿检查，不调用桌面演示文稿应用：

```powershell
python -m research2slides.cli.app qa examples\phase5\paper-reading --no-render --no-repair
```

Phase 8 一键执行完整链路并打包交付物：

```powershell
python -m research2slides.cli.app build paper.pdf `
  --latex source.tar `
  --workspace workspace\paper `
  --mode paper-reading `
  --language-profile zh_cn_bilingual_terms `
  --theme group-meeting `
  --analysis-draft analysis_draft.json `
  --storyline-draft storyline_draft.json `
  --slide-spec-draft slide_spec_draft.json
```

`build` 按 `parse -> understand -> plan -> spec -> render -> qa -> package` 顺序执行，将步骤状态原子写入 `build_checkpoint.json`。中断后使用相同命令会自动跳过已完成且 artifact 有效的步骤；也可用 `--resume-from render` 显式从指定步骤继续。最终交付物统一写入 `workspace\delivery`。

Phase 9 Semantic QA 2.0 可使用离线审计 draft：

```powershell
python -m research2slides.cli.app qa workspace\paper `
  --semantic-draft semantic_qa_draft.json
```

也可以调用 Responses API evaluator：

```powershell
python -m research2slides.cli.app qa workspace\paper `
  --semantic `
  --model gpt-5.6-sol `
  --reasoning-effort high
```

一键构建使用 `--semantic-qa-draft` 或 `--semantic-qa` 接入同一检查。输出 `data\semantic_qa.json`，逐页记录 claim-evidence 蕴含、claim strength 与必要叙事依赖；Evaluator 只能报告问题，不能自动改写科学内容。

Phase 10 基准：

```powershell
python scripts\run_semantic_benchmark.py examples\phase10\benchmark.json `
  --output examples\phase10\output
```

基准配置与 runner 都是通用的；论文路径、人工 draft 与注入错误定义保存在 JSON 配置中，不写入核心 QA 逻辑。

需要压缩到目标时间时，完整版本仍会保留：

```powershell
python -m research2slides.cli.app plan workspace\vit `
  --mode paper-reading `
  --draft tests\fixtures\vision_transformer\storyline_paper_reading.json `
  --time-minutes 10
```

输出：

```text
workspace/
├── data/
│   ├── paper_structure.json
│   ├── visual_manifest.json
│   ├── source_manifest.json
│   ├── scientific_understanding.json
│   ├── evidence_graph.json
│   ├── presentation_plan.full.json
│   ├── presentation_plan.json
│   └── slide_spec.json
├── speaker_notes.md
├── presentation_outline.md
├── assets/
│   ├── figures/
│   ├── tables/
│   └── equations/
├── output/
    ├── preview/
    │   ├── slide_001.png
    │   └── ...
    ├── presentation.pptx
    ├── presentation.pdf
    ├── presentation.render.json
    ├── quality_report.json
    ├── quality_report.md
    └── quality_report.manifest.json
├── build_checkpoint.json
└── delivery/
    ├── presentation.pptx
    ├── presentation.pdf
    ├── speaker_notes.md
    ├── presentation_outline.md
    ├── quality_report.json
    └── quality_report.md
```

## 验收

```powershell
python -m pytest -q
npm test
python scripts/export_schemas.py --check
python .agents\skills\research-presentation\scripts\validate_artifacts.py examples\phase5\paper-reading\data
python scripts\validate_pptx.py examples\phase5\paper-reading\output\presentation.pptx --expected-slides 6 --require-notes --require-native-table --require-editable-equation --require-svg
```

如果运行环境的 `TEMP` 目录不可写（受限沙箱），pytest 会报 `PermissionError` 并让大量用例错误退出；改用项目内的基线临时目录即可：

```powershell
python -m pytest -q --basetemp=.pytest_tmp -p no:cacheprovider
```

fixture 可重建：

```powershell
python tests\fixtures\build_fixtures.py
```

## 开发阶段

1. ✅ PDF/LaTeX -> structured document + assets
2. ✅ scientific understanding + evidence graph
3. ✅ storyline + presentation plan
4. ✅ slide spec + speaker notes
5. ✅ PptxGenJS renderer + themes
5.1. ✅ Chinese-first + bilingual technical terms
6. ✅ visual/factual/storyline/presentation QA + evidence-preserving repair loop
7. ✅ 三篇真实公开论文端到端验证 + 26 页人工逐页验收
8. ✅ 一键 build + checkpoint/resume + QA gate + delivery package；DeepSeek-V3 9 页样例验收
9. ✅ Semantic QA 2.0：claim-evidence entailment + claim strength calibration + storyline dependency；DeepSeek-V3 9/9 页复跑
10. ✅ 三篇真实论文、26 页人工基准；12/12 注入错误命中，0 个额外 finding
11. ✅ `0.2.0` wheel + prompt packaging + version/doctor + 隔离安装与 parse smoke test
12. ✅ Windows 离线完整包 + 22 个 Python dependency wheels + node_modules + 1036 文件 checksum + 端到端 PPTX smoke test

每个阶段只有在 fixture、测试、example output、README 和验收记录同时成立时才算完成。
