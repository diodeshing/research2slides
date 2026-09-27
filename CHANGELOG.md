# Changelog

## 未发布

### 修复

- 解析：`_clean_text` 不再把转义百分号 `\%` 当成注释起点，含百分比的段落与表格 caption 不再被静默截断（此前 `Cube success (\%)` 会变成 `Cube success (\`，正文数字后半句丢失）。`\%` 统一还原为 `%`。
- 校验：新增 `research2slides.numbers`，用数值比较替代 token 字符串比较。此前 PDF 抽取把数字与字母粘连（`from42.2%to71.1%`）会让 `71.1`、`0.863` 这类真实数值被判为"来源中不存在"，三处校验（Evidence Graph、Storyline、Factual QA）口径也各不相同；现在统一按数值归一化比较（`3.7` / `3.70` / `.07` / `3.7%` 等价），虚构数值仍然被拒。
- Slide Spec：`_citation` 对同一来源的重复标签去重，长引用不再折行压到页码。
- Slide Spec：`table_column_labels` 的列数校验改为读取 tabular 声明的列定义，与渲染器口径一致。此前多行分组表头（分组行单元数少于实际列数）会导致任何标签集合都被拒绝。
- QA：导出 PPTX/PDF 的子进程统一按 UTF-8 解码（`errors="replace"`），不再因 GBK 字节触发 `UnicodeDecodeError` 并丢失错误输出。

### 文档

- AGENTS.md 与 README 补充受限环境下 pytest 的验收命令（`--basetemp=.pytest_tmp -p no:cacheprovider`），`.gitignore` 忽略该目录。

## 0.2.0 — 2026-09-27

- 完成 Phase 1–10：解析、证据图、叙事规划、Slide Spec、Renderer、QA、一键构建、Semantic QA 与三论文基准。
- 新增 `research2slides version` 与 `research2slides doctor`。
- Prompt assets 随 wheel 安装。
- Renderer 支持通过 `RESEARCH2SLIDES_RENDERER_ROOT` 指向源码 checkout。
- 新增 wheel 构建和隔离安装冒烟检查。

## 0.1.0

- 初始开发版本。
