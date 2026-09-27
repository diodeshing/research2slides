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


TRAILING_TITLE_PUNCTUATION = "。！？!?；;：:"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}|\d+(?:\.\d+)?|[\u4e00-\u9fff]{2,}")


def _keyword_overlap(left: str, right: str) -> bool:
    left_tokens = set(TOKEN_RE.findall(left.casefold()))
    right_tokens = set(TOKEN_RE.findall(right.casefold()))
    if left_tokens & right_tokens:
        return True
    left_cjk = "".join(re.findall(r"[\u4e00-\u9fff]", left))
    right_cjk = "".join(re.findall(r"[\u4e00-\u9fff]", right))
    left_bigrams = {left_cjk[index:index + 2] for index in range(max(0, len(left_cjk) - 1))}
    right_bigrams = {right_cjk[index:index + 2] for index in range(max(0, len(right_cjk) - 1))}
    return bool(left_bigrams & right_bigrams)


def check_presentation(plan: PresentationPlan, spec: SlideSpec) -> tuple[list[QAIssue], int]:
    issues: list[QAIssue] = []
    checks_run = 3
    if spec.estimated_total_seconds != plan.estimated_total_seconds:
        issues.append(
            issue(
                QACategory.PRESENTATION,
                "TIMING_DRIFT",
                QASeverity.ERROR,
                "Slide Spec 与 Presentation Plan 的总讲述时间不一致。",
                repairability=Repairability.NONE,
                suggested_action="重新生成 Slide Spec，并保留每个 unit 的时间预算。",
            )
        )
    if plan.compression and spec.estimated_total_seconds > plan.compression.time_budget_seconds:
        issues.append(
            issue(
                QACategory.PRESENTATION,
                "TIME_BUDGET_EXCEEDED",
                QASeverity.ERROR,
                "压缩后的汇报仍超过用户时间预算。",
                suggested_action="回到 deterministic compression 调整页面选择。",
            )
        )

    for index, slide in enumerate(spec.slides):
        checks_run += 5
        notes = slide.speaker_notes
        if notes.main_message != slide.main_claim:
            issues.append(
                issue(
                    QACategory.PRESENTATION,
                    "NOTES_MAIN_MESSAGE_DRIFT",
                    QASeverity.ERROR,
                    f"{slide.slide_id} 的 speaker notes main message 与页面 main claim 不一致。",
                    slide_ids=[slide.slide_id],
                    suggested_action="以 Slide Spec 的 main claim 为准重新生成讲稿。",
                )
            )
        if notes.purpose != slide.purpose:
            issues.append(
                issue(
                    QACategory.PRESENTATION,
                    "NOTES_PURPOSE_DRIFT",
                    QASeverity.WARNING,
                    f"{slide.slide_id} 的 speaker notes purpose 与页面 purpose 不一致。",
                    slide_ids=[slide.slide_id],
                    suggested_action="统一页面目的与讲稿目的。",
                )
            )
        if not _keyword_overlap(f"{slide.title} {slide.main_claim}", notes.script):
            issues.append(
                issue(
                    QACategory.PRESENTATION,
                    "SCRIPT_CONTENT_DRIFT",
                    QASeverity.WARNING,
                    f"{slide.slide_id} 的讲稿与标题和 main claim 缺少可识别的关键词重合。",
                    slide_ids=[slide.slide_id],
                    suggested_action="人工核对讲稿是否真正解释了页面核心信息。",
                )
            )
        if slide.title.rstrip().endswith(tuple(TRAILING_TITLE_PUNCTUATION)):
            issues.append(
                issue(
                    QACategory.PRESENTATION,
                    "TITLE_TRAILING_PUNCTUATION",
                    QASeverity.WARNING,
                    f"{slide.slide_id} 的短标题包含不必要的结尾标点。",
                    slide_ids=[slide.slide_id],
                    field_path=f"slides[{index}].title",
                    repairability=Repairability.AUTOMATIC,
                    suggested_action="删除标题结尾标点，不改变标题语义或证据。",
                )
            )
        is_last = index == len(spec.slides) - 1
        if not is_last and "结束" in notes.transition:
            issues.append(
                issue(
                    QACategory.PRESENTATION,
                    "EARLY_CLOSING_TRANSITION",
                    QASeverity.WARNING,
                    f"{slide.slide_id} 在最后一页之前使用了结束型 transition。",
                    slide_ids=[slide.slide_id],
                    suggested_action="改写 transition，使其自然引向下一页。",
                )
            )
        if is_last and not any(word in notes.transition for word in ("结束", "问答", "讨论")):
            issues.append(
                issue(
                    QACategory.PRESENTATION,
                    "MISSING_CLOSING_TRANSITION",
                    QASeverity.INFO,
                    f"{slide.slide_id} 的最后 transition 没有明确结束、问答或讨论。",
                    slide_ids=[slide.slide_id],
                    suggested_action="人工决定是否加入结束或 Q&A 提示。",
                )
            )
    return issues, checks_run
