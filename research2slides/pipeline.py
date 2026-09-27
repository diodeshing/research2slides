from __future__ import annotations

import re
from pathlib import Path

from research2slides.artifacts import read_model, write_model
from research2slides.assets.extractor import AssetExtractor
from research2slides.ingestion.document import build_source_manifest
from research2slides.ingestion.latex import materialize_latex
from research2slides.models import PaperStructure, SourceManifest, VisualManifest
from research2slides.parsing.latex_parser import LatexParser
from research2slides.parsing.merge import merge_pdf_and_latex
from research2slides.parsing.pdf_parser import PdfParser


def _paper_id(title: str, fingerprint: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:48] or "paper"
    return f"{slug}-{fingerprint[:10]}"


def _can_resume(data_dir: Path, manifest: SourceManifest) -> bool:
    paths = [
        data_dir / "source_manifest.json",
        data_dir / "paper_structure.json",
        data_dir / "visual_manifest.json",
    ]
    if not all(path.is_file() for path in paths):
        return False
    try:
        old = read_model(paths[0], SourceManifest)
        read_model(paths[1], PaperStructure)
        read_model(paths[2], VisualManifest)
    except Exception:
        return False
    return old.combined_sha256 == manifest.combined_sha256


def parse_sources(
    pdf_path: Path,
    workspace: Path,
    latex_path: Path | None = None,
    force: bool = False,
) -> tuple[PaperStructure, VisualManifest, SourceManifest, bool]:
    pdf_path = pdf_path.resolve()
    latex_path = latex_path.resolve() if latex_path else None
    workspace = workspace.resolve()
    data_dir = workspace / "data"
    asset_dir = workspace / "assets"
    source_manifest = build_source_manifest(pdf_path, latex_path)

    if not force and _can_resume(data_dir, source_manifest):
        return (
            read_model(data_dir / "paper_structure.json", PaperStructure),
            read_model(data_dir / "visual_manifest.json", VisualManifest),
            source_manifest,
            True,
        )

    preliminary_id = f"paper-{source_manifest.combined_sha256[:10]}"
    paper = PdfParser().parse(pdf_path, preliminary_id)
    paper.paper_id = _paper_id(paper.metadata.title, source_manifest.combined_sha256)

    if latex_path:
        with materialize_latex(latex_path) as latex_root:
            latex = LatexParser().parse(latex_root)
            paper = merge_pdf_and_latex(paper, latex)
            paper.paper_id = _paper_id(paper.metadata.title, source_manifest.combined_sha256)
            visuals = AssetExtractor().extract(paper, pdf_path, asset_dir, latex_root, latex)
    else:
        visuals = AssetExtractor().extract(paper, pdf_path, asset_dir)

    visuals.paper_id = paper.paper_id
    write_model(data_dir / "paper_structure.json", paper)
    write_model(data_dir / "visual_manifest.json", visuals)
    write_model(data_dir / "source_manifest.json", source_manifest)
    return paper, visuals, source_manifest, False

