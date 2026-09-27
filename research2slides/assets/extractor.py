from __future__ import annotations

import hashlib
import mimetypes
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops
from pypdf import PdfReader

from research2slides.assets.figure_matcher import resolve_graphic
from research2slides.ingestion.document import sha256_file
from research2slides.models import AssetKind, AssetOrigin, PaperStructure, VisualAsset, VisualManifest
from research2slides.parsing.latex_parser import LatexParseResult


VECTOR_EXTENSIONS = {".pdf", ".svg", ".eps"}


def _asset_id(prefix: str, seed: str) -> str:
    return f"{prefix}_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _materialize_latex_visual(source: Path, target_stem: Path) -> Path:
    if source.suffix.lower() != ".pdf":
        target = target_stem.with_suffix(source.suffix.lower())
        shutil.copy2(source, target)
        return target
    target = target_stem.with_suffix(".png")
    try:
        with pymupdf.open(source) as document:
            if document.page_count < 1:
                raise ValueError("PDF visual has no pages")
            pixmap = document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            pixmap.save(target)
        with Image.open(target) as image:
            rgb = image.convert("RGB")
            white = Image.new("RGB", rgb.size, "white")
            difference = ImageChops.difference(rgb, white).convert("L")
            bounds = difference.point(lambda value: 255 if value > 4 else 0).getbbox()
            if bounds:
                padding = 24
                left = max(0, bounds[0] - padding)
                top = max(0, bounds[1] - padding)
                right = min(rgb.width, bounds[2] + padding)
                bottom = min(rgb.height, bounds[3] + padding)
                rgb.crop((left, top, right, bottom)).save(target)
    except Exception as exc:
        raise ValueError(f"Unable to rasterize PDF visual {source}: {exc}") from exc
    return target


class AssetExtractor:
    def extract(
        self,
        paper: PaperStructure,
        pdf_path: Path,
        output_root: Path,
        latex_root: Path | None = None,
        latex: LatexParseResult | None = None,
    ) -> VisualManifest:
        figure_dir = output_root / "figures"
        table_dir = output_root / "tables"
        equation_dir = output_root / "equations"
        for directory in (figure_dir, table_dir, equation_dir):
            directory.mkdir(parents=True, exist_ok=True)

        assets: list[VisualAsset] = []
        if latex_root and latex:
            for figure in latex.figures:
                if not figure.source_file:
                    continue
                source = resolve_graphic(latex_root, latex.main_file, figure.source_file)
                if not source:
                    paper.provenance.warnings.append(
                        f"LaTeX figure asset not found for {figure.figure_id}: {figure.source_file}"
                    )
                    continue
                origin = AssetOrigin.LATEX_VECTOR if source.suffix.lower() in VECTOR_EXTENSIONS else AssetOrigin.LATEX_RASTER
                try:
                    target = _materialize_latex_visual(source, figure_dir / figure.figure_id)
                except ValueError as exc:
                    paper.provenance.warnings.append(str(exc))
                    continue
                assets.append(
                    VisualAsset(
                        asset_id=_asset_id("asset", f"latex:{source.relative_to(latex_root).as_posix()}"),
                        type=AssetKind.FIGURE,
                        origin=origin,
                        priority=1 if origin == AssetOrigin.LATEX_VECTOR else 2,
                        source_path=source.relative_to(latex_root).as_posix(),
                        output_path=target.relative_to(output_root.parent).as_posix(),
                        sha256=sha256_file(target),
                        number=figure.number,
                        caption=figure.caption,
                        related_section=figure.related_section,
                        source_label=figure.label,
                        media_type=mimetypes.guess_type(target.name)[0],
                    )
                )

        self._extract_pdf_images(pdf_path, figure_dir, output_root, paper, assets)
        assets.sort(key=lambda item: (item.priority, item.asset_id))
        return VisualManifest(paper_id=paper.paper_id, assets=assets)

    def _extract_pdf_images(
        self,
        pdf_path: Path,
        figure_dir: Path,
        output_root: Path,
        paper: PaperStructure,
        assets: list[VisualAsset],
    ) -> None:
        try:
            reader = PdfReader(str(pdf_path))
            for page_number, page in enumerate(reader.pages, start=1):
                for index, image in enumerate(page.images, start=1):
                    suffix = Path(image.name).suffix.lower() or ".bin"
                    seed = f"pdf:{page_number}:{index}:{image.name}"
                    asset_id = _asset_id("asset", seed)
                    target = figure_dir / f"{asset_id}{suffix}"
                    target.write_bytes(image.data)
                    assets.append(
                        VisualAsset(
                            asset_id=asset_id,
                            type=AssetKind.FIGURE,
                            origin=AssetOrigin.PDF_EMBEDDED,
                            priority=3,
                            source_path=f"{pdf_path.name}#page={page_number};image={index}",
                            output_path=target.relative_to(output_root.parent).as_posix(),
                            sha256=sha256_file(target),
                            page=page_number,
                            media_type=mimetypes.guess_type(target.name)[0],
                        )
                    )
        except Exception as exc:
            paper.provenance.warnings.append(f"PDF embedded image extraction failed: {exc}")
