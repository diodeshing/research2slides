from pathlib import Path

import pymupdf
import pytest

from research2slides.artifacts import read_model
from research2slides.models import AssetOrigin, PaperStructure, VisualManifest
from research2slides.assets.extractor import _materialize_latex_visual
from research2slides.pipeline import parse_sources


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture", "expected_title", "expected_origin"),
    [
        ("attention_is_all_you_need", "Attention Is All You Need", AssetOrigin.LATEX_VECTOR),
        ("vision_transformer", "An Image is Worth 16x16 Words", AssetOrigin.LATEX_RASTER),
    ],
)
def test_phase1_pipeline_end_to_end(
    tmp_path: Path,
    fixture: str,
    expected_title: str,
    expected_origin: AssetOrigin,
) -> None:
    source = FIXTURES / fixture
    workspace = tmp_path / fixture
    paper, visuals, _, resumed = parse_sources(
        source / "paper.pdf",
        workspace,
        source / "source.zip",
    )
    assert resumed is False
    assert paper.metadata.title == expected_title
    assert paper.page_count == 2
    assert len(paper.sections) >= 3
    assert paper.figures and paper.tables and paper.equations
    assert visuals.assets[0].origin == expected_origin
    assert (workspace / visuals.assets[0].output_path).is_file()
    assert read_model(workspace / "data" / "paper_structure.json", PaperStructure) == paper
    assert read_model(workspace / "data" / "visual_manifest.json", VisualManifest) == visuals

    _, _, _, resumed = parse_sources(source / "paper.pdf", workspace, source / "source.zip")
    assert resumed is True


def test_force_disables_resume(tmp_path: Path) -> None:
    source = FIXTURES / "attention_is_all_you_need"
    workspace = tmp_path / "paper"
    parse_sources(source / "paper.pdf", workspace, source / "source.zip")
    _, _, _, resumed = parse_sources(source / "paper.pdf", workspace, source / "source.zip", force=True)
    assert resumed is False


def test_pdf_figure_is_materialized_as_renderable_png(tmp_path: Path) -> None:
    source = tmp_path / "figure.pdf"
    with pymupdf.open() as document:
        document.new_page(width=320, height=180)
        document.save(source)
    target = _materialize_latex_visual(source, tmp_path / "figure")
    assert target.suffix == ".png"
    assert target.is_file()
    assert target.stat().st_size > 0
