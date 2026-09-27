from __future__ import annotations

import re

from research2slides.models import (
    PresentationPlan,
    QACategory,
    QAIssue,
    QASeverity,
    Repairability,
    SlideSpec,
)
from research2slides.qa.common import issue


METHOD_ROLES = {"core_insight", "contributions", "method_overview", "method_component"}
EVIDENCE_ROLES = {"experiments", "ablation", "analysis"}
ENDING_ROLES = {"conclusion", "takeaway"}


def _normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).casefold()


def check_storyline(plan: PresentationPlan, spec: SlideSpec) -> tuple[list[QAIssue], int]:
    issues: list[QAIssue] = []
    checks_run = 5
    units = {unit.unit_id: unit for unit in plan.units}

    if [slide.unit_id for slide in spec.slides] != [unit.unit_id for unit in plan.units]:
        issues.append(
            issue(
                QACategory.STORYLINE,
                "PLAN_SPEC_ORDER_MISMATCH",
                QASeverity.ERROR,
                "Slide Spec 与 Presentation Plan 的 unit 顺序不一致。",
                repairability=Repairability.NONE,
                suggested_action="重新运行 Slide Authoring，不能由 QA 猜测页面顺序。",
            )
        )

    roles = [unit.role for unit in plan.units]
    required_groups = {
        "problem": {"problem"},
        "method": METHOD_ROLES,
        "evidence": EVIDENCE_ROLES,
        "ending": ENDING_ROLES,
    }
    for name, accepted in required_groups.items():
        if not any(role in accepted for role in roles):
            issues.append(
                issue(
                    QACategory.STORYLINE,
                    "MISSING_STORYLINE_STAGE",
                    QASeverity.ERROR,
                    f"叙事缺少 {name} 阶段。",
                    repairability=Repairability.NONE,
                    suggested_action="回到 Presentation Plan 补齐证据支持的叙事单元。",
                )
            )
    if "limitations" not in roles:
        issues.append(
            issue(
                QACategory.STORYLINE,
                "MISSING_LIMITATIONS",
                QASeverity.WARNING,
                "汇报没有独立的 limitations 页面。",
                suggested_action="人工确认论文是否确实没有可讲的限制，或补充受证据支持的限制页面。",
            )
        )

    def first_index(accepted: set[str]) -> int:
        return min((index for index, role in enumerate(roles) if role in accepted), default=10**6)

    sequence = [first_index({"problem"}), first_index(METHOD_ROLES), first_index(EVIDENCE_ROLES), first_index(ENDING_ROLES)]
    if sequence != sorted(sequence):
        issues.append(
            issue(
                QACategory.STORYLINE,
                "STORYLINE_ORDER",
                QASeverity.ERROR,
                "Problem、Method、Evidence 与 Conclusion 的顺序出现倒置。",
                repairability=Repairability.NONE,
                suggested_action="在 Presentation Plan 中重排 units，并重新生成 Slide Spec。",
            )
        )

    seen_claims: dict[str, str] = {}
    for slide in spec.slides:
        normalized = _normalize(slide.main_claim)
        if normalized in seen_claims:
            issues.append(
                issue(
                    QACategory.STORYLINE,
                    "DUPLICATE_MAIN_CLAIM",
                    QASeverity.WARNING,
                    f"{slide.slide_id} 与 {seen_claims[normalized]} 使用了相同 main claim。",
                    slide_ids=[seen_claims[normalized], slide.slide_id],
                    suggested_action="合并重复页面，或明确两页分别回答的不同问题。",
                )
            )
        seen_claims[normalized] = slide.slide_id
        unit = units.get(slide.unit_id)
        if unit and (
            slide.question != unit.question
            or slide.main_claim != unit.main_claim
            or slide.evidence_ids != unit.evidence_ids
        ):
            issues.append(
                issue(
                    QACategory.STORYLINE,
                    "UNIT_CONTENT_DRIFT",
                    QASeverity.ERROR,
                    f"{slide.slide_id} 与对应 presentation unit 的 question、claim 或 evidence 不一致。",
                    slide_ids=[slide.slide_id],
                    evidence_ids=slide.evidence_ids,
                    repairability=Repairability.NONE,
                    suggested_action="重新运行 Slide Authoring，保持 Plan 到 Spec 的锁定字段。",
                )
            )

    for gap in plan.coverage_gaps:
        issues.append(
            issue(
                QACategory.STORYLINE,
                "DECLARED_COVERAGE_GAP",
                QASeverity.WARNING,
                f"Presentation Plan 明确记录 coverage gap：{gap}。",
                suggested_action="人工确认该缺口源于证据不足还是时间压缩；不要自动补写内容。",
            )
        )
    return issues, checks_run + len(spec.slides)
