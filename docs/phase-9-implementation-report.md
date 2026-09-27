# Phase 9 — Semantic QA 2.0 实现与验收报告

状态：Complete  
日期：2026-09-27

## 目标

Phase 7 的真实论文验收表明，Phase 6 能验证引用存在、数字来源、artifact 一致性和渲染几何，但不能回答三个语义问题：页面 claim 是否真的由证据推出、措辞是否强于证据、关键概念是否在使用前完成铺垫。Phase 9 只补这三项，不扩展自动修复权限。

## 实现

- 新增 `SemanticQADraft`、`SemanticQAResult` 与两份 JSON Schema。
- 新增离线 JSON provider 与 OpenAI-compatible Responses provider；远程输出使用 strict Structured Outputs。
- 新增逐页 claim-evidence entailment、claim-strength calibration 与 storyline dependency 检查。
- 本地 gate 强制 evaluation 与 Slide Spec 页序完全一致，evidence 只能来自本页，依赖只能引用已知页面。
- 新增 `data/semantic_qa.json` 与 fingerprint manifest，可安全复用相同 evaluator 结果。
- `qa` 支持 `--semantic-draft` 和 `--semantic`；`build` 支持 `--semantic-qa-draft` 和 `--semantic-qa`。
- Phase 8 checkpoint/build 升级为 `phase9-v1`，Semantic QA 开启时把结果纳入 QA 完成条件与 delivery package。
- 所有 Semantic QA finding 均禁止自动修复。

## 错误语义

| 检查 | 结果 | 严重度 |
|---|---|---:|
| Claim-evidence | unsupported | error |
| Claim-evidence | partially supported / insufficient | warning |
| Claim strength | overstated | error |
| Claim strength | understated | info |
| Storyline dependency | missing / late prerequisite | warning |

## 回归覆盖

新增测试覆盖：

- 合法 evaluator 结果生成与 fingerprint 复用。
- Unsupported、partial、overstated 三类语义问题。
- 叙事前置依赖倒置。
- 跨页借用 evidence 被本地拒绝。
- Responses API strict schema、High reasoning 配置与 `store=false`。
- Quality Report 记录三项 semantic checks。
- 一键 build 将 `semantic_qa.json` 打入 delivery。

## DeepSeek-V3 真实复跑

- 页面：9
- Semantic evaluations：9/9
- Claim-evidence：全部 entailed
- Claim strength：全部 calibrated
- Storyline dependencies：全部在使用前满足
- 最终 QA：`pass_with_warnings`
- 唯一告警：原有 `DECLARED_COVERAGE_GAP: research gap`
- PPTX：未修改；仅从 QA checkpoint 继续并重新打包

该离线 draft 是可审计验收基准，不代表模型 evaluator 永远正确。生产运行仍应抽查 source excerpt 与结论边界。

## 最终验证

- Python：59 passed
- Renderer：15 passed
- Schema export check：通过
- DeepSeek-V3 artifact validation：通过
- 9 页 PPTX、speaker notes 与 native table：通过
- 含 Semantic QA 的相同 build 二次执行：1.2 秒完成，checkpoint 全量复用
- 工作区治理测试：24 passed
- 严格工作区自检：0 error、1 warning；警告为根 `.git` 缺少 `HEAD` 的既有工作区问题
