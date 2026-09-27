# Phase 7 QA Gap Analysis

本报告比较自动 QA 与 26 页人工全尺寸复核的差异。严重度定义：P0 阻断/事实错误；P1 影响可读性或证据表达；P2 可用但需后续增强；P3 轻微体验问题。

## 已发现并修复

| 严重度 | 问题 | 自动 QA | 修复 |
|---|---|---|---|
| P1 | 官方 arXiv TAR source 无法 ingest | 未覆盖真实 archive | 增加 TAR/TAR.GZ/TGZ 安全解包与测试 |
| P1 | 标题中的 LaTeX 格式/宏污染 | 未捕获 | 改进标题规范化与宏匹配顺序 |
| P1 | `figure*`、`table*` 等 starred 环境丢失 | 未捕获 | parser 支持 starred floats/equations |
| P1 | PDF Figure 不能直接作为 PPTX 图片 | Renderer 失败才暴露 | PyMuPDF 首页面栅格化，保留 source provenance |
| P1 | PDF Figure 大白边导致主体过小 | 视觉 QA 未捕获 | Pillow 自动裁剪纯白边距并留安全 padding |
| P1 | 复杂 LaTeX table 命令泄漏、表格溢出 | 几何 QA 未捕获 | 通用清洗、动态字号/行高、highlight 证据视图 |
| P1 | 嵌套 `tabular` 列格式被误识别成首行 | 视觉 QA 未捕获 | 使用平衡花括号解析列定义并添加回归测试 |
| P1 | 原始公式 LaTeX 可读性差、窄图无信息增益 | 视觉 QA 未捕获 | 公式清理为可编辑文本，删除无助解释的视觉 |
| P1 | SAM 消融页正文遮挡坐标轴 | 视觉 QA 未捕获 | 改用左右分栏布局 |
| P1 | NIAH 说明覆盖原图标题 | 视觉 QA 未捕获 | 删除冗余覆盖注释 |
| P1 | A 的限制内容存在但 role 未明确 | 自动 QA 正确报警 | 将对应 unit 明确标为 `limitations` |

最终结果：P0 = 0；关键 P1 = 0。三套 deck 的结构、事实、视觉文件和讲稿层均无 error。

## 自动 QA 的 false negatives

- OOXML 几何合法不等于内容可读：表格可以在边界内但字号过小、命令泄漏或语义首行错误。
- 图片存在且未越界不等于主体足够大：PDF 白边与稀疏原图会让核心信息缩小。
- 文本框未越界不等于未遮挡原图关键信息：SAM 消融页与 NIAH 图均需人工视觉判断。
- 公式字段有效不等于公式适合演示：复杂 LaTeX 与窄源图需要针对讲述目标取舍。

## 自动 QA 的 true positives 与保留警告

- A 的 missing-limitations 检查准确指出“内容存在但叙事角色未声明”，修复后清零。
- B、C 的 `DECLARED_COVERAGE_GAP: research gap` 是有效的证据边界提示。人工确认源证据不足后保留警告，避免用模型臆测消除它。
- 最终没有判定为无效的自动错误；两个 warning 均属于审计信息，不影响交付。

## 后续 P2 / P3

- P2：增加复杂表格的视觉语义检查，例如识别疑似 LaTeX 列格式、异常空白首行和过小字号。
- P2：对自定义 LaTeX 宏做受限、安全的 caption/text 展开。
- P2：manifest 按 source hash + page 去重重复视觉。
- P3：当前主题偏保守，满足组会可读性，但尚未针对不同实验室或会议建立更丰富的品牌化视觉系统。
