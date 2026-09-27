from __future__ import annotations

import math
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from research2slides.models import (
    QACategory,
    QAIssue,
    QASeverity,
    Repairability,
    SlideSpec,
)
from research2slides.qa.common import issue


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
EMU_PER_INCH = 914400
SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml$")


@dataclass(frozen=True)
class TextBox:
    text: str
    x: int
    y: int
    cx: int
    cy: int
    min_font_pt: float | None
    auto_fit: bool


def _slide_number(name: str) -> int:
    match = SLIDE_RE.search(name)
    return int(match.group(1)) if match else 10**9


def _text_boxes(root: ET.Element) -> list[TextBox]:
    boxes: list[TextBox] = []
    for shape in root.findall(".//p:sp", NS):
        text = "".join(node.text or "" for node in shape.findall(".//a:t", NS)).strip()
        if not text:
            continue
        transform = shape.find("./p:spPr/a:xfrm", NS)
        if transform is None:
            continue
        offset = transform.find("./a:off", NS)
        extent = transform.find("./a:ext", NS)
        if offset is None or extent is None:
            continue
        try:
            x = int(offset.attrib["x"])
            y = int(offset.attrib["y"])
            cx = int(extent.attrib["cx"])
            cy = int(extent.attrib["cy"])
        except (KeyError, ValueError):
            continue
        sizes = []
        for props in shape.findall(".//a:rPr", NS) + shape.findall(".//a:defRPr", NS):
            raw = props.attrib.get("sz")
            if raw and raw.isdigit():
                sizes.append(int(raw) / 100)
        auto_fit = shape.find(".//a:normAutofit", NS) is not None or shape.find(".//a:spAutoFit", NS) is not None
        boxes.append(TextBox(text, x, y, cx, cy, min(sizes) if sizes else None, auto_fit))
    return boxes


def _intersection_ratio(left: TextBox, right: TextBox) -> float:
    width = max(0, min(left.x + left.cx, right.x + right.cx) - max(left.x, right.x))
    height = max(0, min(left.y + left.cy, right.y + right.cy) - max(left.y, right.y))
    if width == 0 or height == 0:
        return 0.0
    intersection = width * height
    smaller = min(left.cx * left.cy, right.cx * right.cy)
    return intersection / smaller if smaller else 0.0


def _looks_overfull(box: TextBox) -> bool:
    if box.auto_fit or not box.min_font_pt or box.cx <= 0 or box.cy <= 0:
        return False
    width_inches = box.cx / EMU_PER_INCH
    height_inches = box.cy / EMU_PER_INCH
    weighted = sum(1.0 if "\u4e00" <= char <= "\u9fff" else 0.55 for char in box.text)
    chars_per_line = max(1.0, width_inches * 72 / box.min_font_pt)
    required_lines = math.ceil(weighted / chars_per_line)
    required_height = required_lines * box.min_font_pt * 1.28 / 72
    return required_height > height_inches * 1.15


def _png_size(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", header[16:24])
    except OSError:
        return None


def inspect_visuals(
    pptx_path: Path,
    spec: SlideSpec,
    preview_dir: Path | None,
) -> tuple[list[QAIssue], int, dict[str, object]]:
    issues: list[QAIssue] = []
    checks_run = 6
    metrics: dict[str, object] = {}
    try:
        with zipfile.ZipFile(pptx_path) as archive:
            names = set(archive.namelist())
            slide_names = sorted((name for name in names if SLIDE_RE.search(name)), key=_slide_number)
            metrics["pptx_slide_count"] = len(slide_names)
            if len(slide_names) != len(spec.slides):
                issues.append(
                    issue(
                        QACategory.VISUAL,
                        "SLIDE_COUNT_MISMATCH",
                        QASeverity.ERROR,
                        f"PPTX 含 {len(slide_names)} 页，但 Slide Spec 定义 {len(spec.slides)} 页。",
                        repairability=Repairability.NONE,
                        suggested_action="重新渲染完整 deck，不能用 partial review deck 作为最终输出。",
                    )
                )
            presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
            size = presentation.find("./p:sldSz", NS)
            slide_width = int(size.attrib.get("cx", "0")) if size is not None else 0
            slide_height = int(size.attrib.get("cy", "0")) if size is not None else 0
            metrics["slide_size_emu"] = [slide_width, slide_height]
            if slide_width <= 0 or slide_height <= 0 or abs(slide_width / slide_height - 16 / 9) > 0.01:
                issues.append(
                    issue(
                        QACategory.VISUAL,
                        "INVALID_SLIDE_ASPECT",
                        QASeverity.ERROR,
                        "PPTX 画布不是有效的 16:9 尺寸。",
                        repairability=Repairability.NONE,
                        suggested_action="检查 Renderer 的 presentation layout 设置。",
                    )
                )
            note_count = len([name for name in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)])
            metrics["notes_slide_count"] = note_count
            if note_count != len(spec.slides):
                issues.append(
                    issue(
                        QACategory.VISUAL,
                        "MISSING_NOTES_PART",
                        QASeverity.ERROR,
                        f"PPTX 只有 {note_count} 个 notes part，预期 {len(spec.slides)} 个。",
                        suggested_action="重新渲染并确认每页调用了 addNotes。",
                    )
                )

            for index, slide_name in enumerate(slide_names):
                if index >= len(spec.slides):
                    break
                slide = spec.slides[index]
                root = ET.fromstring(archive.read(slide_name))
                boxes = _text_boxes(root)
                for box in boxes:
                    if box.x < 0 or box.y < 0 or box.x + box.cx > slide_width or box.y + box.cy > slide_height:
                        issues.append(
                            issue(
                                QACategory.VISUAL,
                                "OUT_OF_BOUNDS_TEXT",
                                QASeverity.ERROR,
                                f"{slide.slide_id} 存在超出画布的文本框。",
                                slide_ids=[slide.slide_id],
                                suggested_action="调整对应 layout/component 的几何参数后重渲染。",
                            )
                        )
                        break
                    if box.min_font_pt is not None and box.min_font_pt < 8:
                        issues.append(
                            issue(
                                QACategory.VISUAL,
                                "UNREADABLY_SMALL_FONT",
                                QASeverity.WARNING,
                                f"{slide.slide_id} 存在小于 8pt 的文本。",
                                slide_ids=[slide.slide_id],
                                suggested_action="缩短文字或扩大文本区域，避免继续缩小字号。",
                            )
                        )
                        break
                    if _looks_overfull(box):
                        issues.append(
                            issue(
                                QACategory.VISUAL,
                                "LIKELY_TEXT_OVERFLOW",
                                QASeverity.WARNING,
                                f"{slide.slide_id} 的文本密度可能超过文本框容量。",
                                slide_ids=[slide.slide_id],
                                suggested_action="检查对应 PNG；优先改写或调整布局，而不是机械缩小字体。",
                            )
                        )
                        break
                overlap_found = False
                for left_index, left in enumerate(boxes):
                    for right in boxes[left_index + 1:]:
                        if (
                            left.y > slide_height * 0.84
                            and right.y > slide_height * 0.84
                        ) or re.fullmatch(r"\d{2}", left.text) or re.fullmatch(r"\d{2}", right.text):
                            continue
                        if _intersection_ratio(left, right) > 0.65:
                            issues.append(
                                issue(
                                    QACategory.VISUAL,
                                    "TEXT_BOX_OVERLAP",
                                    QASeverity.ERROR,
                                    f"{slide.slide_id} 存在大面积重叠的文本框。",
                                    slide_ids=[slide.slide_id],
                                    suggested_action="调整 Renderer 几何参数并仅重渲染该页进行复检。",
                                )
                            )
                            overlap_found = True
                            break
                    if overlap_found:
                        break
                if any(visual.kind == "source_table" for visual in slide.visuals):
                    if root.find(".//a:tbl", NS) is None:
                        issues.append(
                            issue(
                                QACategory.VISUAL,
                                "NATIVE_TABLE_MISSING",
                                QASeverity.ERROR,
                                f"{slide.slide_id} 应包含可编辑 native table，但 PPTX 中未找到。",
                                slide_ids=[slide.slide_id],
                                suggested_action="修复表格 renderer，不能用截图替代要求的可编辑表格。",
                            )
                        )
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        issues.append(
            issue(
                QACategory.VISUAL,
                "INVALID_PPTX_PACKAGE",
                QASeverity.ERROR,
                f"无法检查 PPTX 包：{exc}",
                repairability=Repairability.NONE,
                suggested_action="重新渲染 PPTX 并检查 OOXML package。",
            )
        )
        return issues, checks_run, metrics

    if preview_dir is None:
        issues.append(
            issue(
                QACategory.VISUAL,
                "PREVIEW_NOT_RENDERED",
                QASeverity.WARNING,
                "未生成逐页 PNG，因此视觉 QA 只完成了结构检查。",
                suggested_action="在可用的 Office/PDF 环境中重新运行 qa，生成 PDF 和逐页预览。",
            )
        )
    else:
        previews = sorted(preview_dir.glob("slide_*.png"))
        metrics["preview_count"] = len(previews)
        if len(previews) != len(spec.slides):
            issues.append(
                issue(
                    QACategory.VISUAL,
                    "PREVIEW_COUNT_MISMATCH",
                    QASeverity.ERROR,
                    f"预览目录含 {len(previews)} 张 PNG，预期 {len(spec.slides)} 张。",
                    suggested_action="重新从最终 PDF 生成全部页面预览。",
                )
            )
        for index, preview in enumerate(previews[: len(spec.slides)]):
            dimensions = _png_size(preview)
            slide_id = spec.slides[index].slide_id
            if dimensions is None:
                issues.append(
                    issue(
                        QACategory.VISUAL,
                        "INVALID_PREVIEW_IMAGE",
                        QASeverity.ERROR,
                        f"{preview.name} 不是可读取的 PNG。",
                        slide_ids=[slide_id],
                        suggested_action="重新渲染该页预览。",
                    )
                )
                continue
            width, height = dimensions
            if width < 960 or height < 540 or abs(width / height - 16 / 9) > 0.03:
                issues.append(
                    issue(
                        QACategory.VISUAL,
                        "LOW_QUALITY_PREVIEW",
                        QASeverity.WARNING,
                        f"{preview.name} 的分辨率或宽高比不足：{width}x{height}。",
                        slide_ids=[slide_id],
                        suggested_action="以至少 960x540 的 16:9 分辨率重新渲染。",
                    )
                )
    return issues, checks_run + len(spec.slides), metrics
