from __future__ import annotations

import hashlib
from pathlib import Path

from research2slides.exceptions import InputError
from research2slides.ingestion.latex import is_latex_archive
from research2slides.models import SourceFile, SourceManifest, SourceRole


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        content_hash = sha256_file(item).encode("ascii")
        digest.update(relative + b"\0" + content_hash + b"\0")
        total += item.stat().st_size
    return digest.hexdigest(), total


def build_source_manifest(pdf_path: Path, latex_path: Path | None = None) -> SourceManifest:
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise InputError(f"PDF input does not exist or is not a .pdf file: {pdf_path}")

    sources = [
        SourceFile(
            source_id="source_pdf",
            role=SourceRole.PAPER_PDF,
            path=str(pdf_path),
            sha256=sha256_file(pdf_path),
            size_bytes=pdf_path.stat().st_size,
        )
    ]
    if latex_path is not None:
        latex_path = latex_path.resolve()
        if latex_path.is_dir():
            digest, size = sha256_directory(latex_path)
            role = SourceRole.LATEX_DIRECTORY
        elif latex_path.is_file() and is_latex_archive(latex_path):
            digest, size = sha256_file(latex_path), latex_path.stat().st_size
            role = SourceRole.LATEX_ARCHIVE
        else:
            raise InputError(
                f"LaTeX input must be a directory, ZIP, TAR, TAR.GZ, or TGZ archive: {latex_path}"
            )
        sources.append(
            SourceFile(
                source_id="source_latex",
                role=role,
                path=str(latex_path),
                sha256=digest,
                size_bytes=size,
            )
        )

    combined = hashlib.sha256()
    for source in sources:
        combined.update(source.source_id.encode("utf-8"))
        combined.update(source.sha256.encode("ascii"))
    return SourceManifest(sources=sources, combined_sha256=combined.hexdigest())
