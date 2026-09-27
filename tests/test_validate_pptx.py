from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.validate_pptx import validate


SLIDE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree/></p:cSld>
</p:sld>
"""


def _minimal_pptx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", SLIDE_XML)


def _equation_pptx(path: Path) -> None:
    equation_xml = SLIDE_XML.replace(
        "<p:spTree/>",
        "<p:spTree><p:sp><p:txBody><a:p><a:r><a:t>"
        "Attention(Q, K, V) = softmax((QK^T)/(√(d_k)))V"
        "</a:t></a:r></a:p></p:txBody></p:sp></p:spTree>",
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", equation_xml)


def test_optional_content_is_not_required_for_every_deck(tmp_path: Path) -> None:
    pptx = tmp_path / "minimal.pptx"
    _minimal_pptx(pptx)

    assert validate(pptx, expected_slides=1, require_notes=False, require_table=False) == []


def test_content_requirements_are_explicit(tmp_path: Path) -> None:
    pptx = tmp_path / "minimal.pptx"
    _minimal_pptx(pptx)

    errors = validate(
        pptx,
        expected_slides=1,
        require_notes=False,
        require_table=False,
        require_equation=True,
        require_svg=True,
    )

    assert errors == [
        "no editable equation text was found",
        "no source SVG was preserved in the PPTX media package",
    ]


def test_editable_equation_allows_normal_display_spacing(tmp_path: Path) -> None:
    pptx = tmp_path / "equation.pptx"
    _equation_pptx(pptx)

    assert validate(
        pptx,
        expected_slides=1,
        require_notes=False,
        require_table=False,
        require_equation=True,
    ) == []
