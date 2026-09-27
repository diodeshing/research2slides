from __future__ import annotations

from research2slides.models import SlideSpec


def render_speaker_notes(spec: SlideSpec) -> str:
    lines = [f"# Speaker Notes: {spec.title}", ""]
    for slide in spec.slides:
        notes = slide.speaker_notes
        lines.extend(
            [
                f"## Slide {slide.order}: {slide.title}",
                "",
                "### Purpose",
                "",
                notes.purpose,
                "",
                "### Main Message",
                "",
                notes.main_message,
                "",
                "### Speaking Script",
                "",
                notes.script,
                "",
                "### Visual Guidance",
                "",
                notes.visual_guidance,
                "",
                "### Transition",
                "",
                notes.transition,
                "",
                "### Estimated Time",
                "",
                f"{notes.estimated_seconds} seconds",
                "",
            ]
        )
    lines.extend(
        [
            "## Estimated Total Presentation Time",
            "",
            f"{spec.estimated_total_seconds} seconds ({spec.estimated_total_seconds / 60:.1f} minutes)",
            "",
        ]
    )
    return "\n".join(lines)


def render_presentation_outline(spec: SlideSpec) -> str:
    lines = [f"# 演示提纲：{spec.title}", ""]
    for slide in spec.slides:
        lines.extend(
            [
                f"## Slide {slide.order} — {slide.title}",
                "",
                f"Purpose: {slide.purpose}",
                "",
                f"Core Message: {slide.main_claim}",
                "",
                f"Evidence: {', '.join(slide.evidence_ids)}",
                "",
                f"Estimated Time: {slide.speaker_notes.estimated_seconds} 秒",
                "",
            ]
        )
    lines.extend(
        [f"总计：{len(spec.slides)} 页，{spec.estimated_total_seconds} 秒", ""]
    )
    return "\n".join(lines)
