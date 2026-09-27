from __future__ import annotations

from research2slides.models import QACategory, QASeverity, QualityReport


CATEGORY_LABELS = {
    QACategory.FACTUAL: "事实与证据",
    QACategory.STORYLINE: "叙事结构",
    QACategory.VISUAL: "视觉与文件",
    QACategory.PRESENTATION: "讲述与交付",
}


def render_quality_report(report: QualityReport) -> str:
    lines = [
        "# Research2Slides Quality Report",
        "",
        f"- 状态：`{report.status.value}`",
        f"- 论文 ID：`{report.paper_id}`",
        f"- 模式：`{report.mode.value}`",
        f"- 主题：`{report.theme}`",
        f"- 页数：{report.slide_count}",
        f"- 是否需要人工复核：{'是' if report.manual_review_required else '否'}",
        "",
        "## 分层结果",
        "",
        "| 层级 | 状态 | 检查数 | 问题数 |",
        "|---|---:|---:|---:|",
    ]
    for result in report.categories:
        lines.append(
            f"| {CATEGORY_LABELS[result.category]} | `{result.status.value}` | "
            f"{result.checks_run} | {len(result.issue_ids)} |"
        )
    lines.extend(["", "## 问题清单", ""])
    if not report.issues:
        lines.append("未发现自动检查问题。")
    else:
        for item in report.issues:
            scope = f"（{', '.join(item.slide_ids)}）" if item.slide_ids else ""
            lines.extend(
                [
                    f"### {item.severity.value.upper()} · {item.code}{scope}",
                    "",
                    item.message,
                    "",
                    f"建议：{item.suggested_action}",
                    "",
                ]
            )
    lines.extend(["## Repair History", ""])
    if not report.repairs:
        lines.append("本次没有可安全自动修复的问题，Slide Spec 未被改写。")
    else:
        for iteration in report.repairs:
            lines.append(
                f"- Iteration {iteration.iteration}: {iteration.issue_count_before} → "
                f"{iteration.issue_count_after} 个问题；修复页面 "
                f"{', '.join(map(str, iteration.repaired_slide_numbers)) or '无'}。"
            )
            for action in iteration.actions:
                lines.append(f"  - `{action.slide_id}` `{action.field_path}`：`{action.before}` → `{action.after}`")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- PPTX: `{report.artifacts.pptx}`",
            f"- PDF: `{report.artifacts.pdf or '未生成'}`",
            f"- Preview: `{report.artifacts.preview_dir or '未生成'}`",
            "",
            "## 自动检查边界",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    lines.append("")
    return "\n".join(lines)
