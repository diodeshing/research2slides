from __future__ import annotations

from hashlib import sha256

from research2slides.models import (
    QACategory,
    QACategoryResult,
    QAIssue,
    QASeverity,
    QAStatus,
    Repairability,
)


def issue(
    category: QACategory,
    code: str,
    severity: QASeverity,
    message: str,
    *,
    slide_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    field_path: str | None = None,
    repairability: Repairability = Repairability.MANUAL,
    suggested_action: str,
) -> QAIssue:
    identity = "\x1f".join(
        [
            category.value,
            code,
            message,
            ",".join(slide_ids or []),
            field_path or "",
        ]
    )
    issue_id = f"qa_{sha256(identity.encode('utf-8')).hexdigest()[:12]}"
    return QAIssue(
        issue_id=issue_id,
        category=category,
        code=code,
        severity=severity,
        message=message,
        slide_ids=slide_ids or [],
        evidence_ids=evidence_ids or [],
        source_ids=source_ids or [],
        field_path=field_path,
        repairability=repairability,
        suggested_action=suggested_action,
    )


def category_result(category: QACategory, issues: list[QAIssue], checks_run: int) -> QACategoryResult:
    selected = [item for item in issues if item.category == category]
    status = QAStatus.PASS
    if any(item.severity == QASeverity.ERROR for item in selected):
        status = QAStatus.FAIL
    elif any(item.severity == QASeverity.WARNING for item in selected):
        status = QAStatus.PASS_WITH_WARNINGS
    return QACategoryResult(
        category=category,
        status=status,
        checks_run=checks_run,
        issue_ids=[item.issue_id for item in selected],
    )


def overall_status(issues: list[QAIssue]) -> QAStatus:
    if any(item.severity == QASeverity.ERROR for item in issues):
        return QAStatus.FAIL
    if any(item.severity == QASeverity.WARNING for item in issues):
        return QAStatus.PASS_WITH_WARNINGS
    return QAStatus.PASS
