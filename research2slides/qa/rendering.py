from __future__ import annotations

import base64
import os
import shutil
import subprocess
from pathlib import Path

from research2slides.exceptions import QualityAssuranceError


def _export_with_soffice(pptx_path: Path, pdf_path: Path) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise QualityAssuranceError("LibreOffice executable was not found")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf_path.parent), str(pptx_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    generated = pdf_path.parent / f"{pptx_path.stem}.pdf"
    if result.returncode != 0 or not generated.is_file():
        raise QualityAssuranceError(result.stderr.strip() or result.stdout.strip() or "LibreOffice PDF export failed")
    if generated.resolve() != pdf_path.resolve():
        os.replace(generated, pdf_path)


def _export_with_windows_com(pptx_path: Path, pdf_path: Path) -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        raise QualityAssuranceError("PowerShell was not found for Windows presentation export")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pptx_literal = str(pptx_path).replace("'", "''")
    pdf_literal = str(pdf_path).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
$app = $null
$deck = $null
try {{
  $app = New-Object -ComObject PowerPoint.Application
  try {{ $app.Visible = 0 }} catch {{}}
  $deck = $app.Presentations.Open('{pptx_literal}', $true, $true, $false)
  $deck.SaveAs('{pdf_literal}', 32)
}} finally {{
  if ($deck -ne $null) {{ $deck.Close() }}
  if ($app -ne $null) {{ $app.Quit() }}
}}
"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )
    if result.returncode != 0 or not pdf_path.is_file():
        raise QualityAssuranceError(result.stderr.strip() or result.stdout.strip() or "Windows COM PDF export failed")


def export_pptx_to_pdf(
    pptx_path: Path,
    pdf_path: Path,
    *,
    backend: str = "auto",
    force: bool = False,
) -> str:
    pptx_path = pptx_path.resolve()
    pdf_path = pdf_path.resolve()
    if not pptx_path.is_file():
        raise QualityAssuranceError(f"PPTX does not exist: {pptx_path}")
    if not force and pdf_path.is_file() and pdf_path.stat().st_mtime_ns >= pptx_path.stat().st_mtime_ns:
        return "reused"
    supported = {"auto", "soffice", "windows-com"}
    if backend not in supported:
        raise QualityAssuranceError(f"Unsupported render backend: {backend}")
    errors: list[str] = []
    candidates = [backend] if backend != "auto" else (["windows-com", "soffice"] if os.name == "nt" else ["soffice"])
    for candidate in candidates:
        try:
            if candidate == "windows-com":
                _export_with_windows_com(pptx_path, pdf_path)
            else:
                _export_with_soffice(pptx_path, pdf_path)
            return candidate
        except (QualityAssuranceError, subprocess.SubprocessError, OSError) as exc:
            errors.append(f"{candidate}: {exc}")
    raise QualityAssuranceError("; ".join(errors) or "No PDF export backend is available")


def render_pdf_previews(pdf_path: Path, preview_dir: Path, *, scale: float = 1.6) -> int:
    preview_dir.mkdir(parents=True, exist_ok=True)
    for existing in preview_dir.glob("slide_*.png"):
        existing.unlink()
    try:
        import pymupdf as fitz  # type: ignore[import-not-found]
    except ImportError:
        fitz = None
    if fitz is not None:
        try:
            document = fitz.open(pdf_path)
            for index, page in enumerate(document):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                pixmap.save(preview_dir / f"slide_{index + 1:03d}.png")
            count = document.page_count
            document.close()
            return count
        except (OSError, RuntimeError, ValueError) as exc:
            raise QualityAssuranceError(f"Unable to render PDF previews with PyMuPDF: {exc}") from exc

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise QualityAssuranceError("PyMuPDF or pdftoppm is required to render Phase 6 PNG previews")
    prefix = preview_dir / "page"
    dpi = max(96, round(96 * scale))
    result = subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )
    generated = sorted(preview_dir.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    if result.returncode != 0 or not generated:
        raise QualityAssuranceError(result.stderr.strip() or result.stdout.strip() or "pdftoppm preview rendering failed")
    for index, source in enumerate(generated, start=1):
        source.replace(preview_dir / f"slide_{index:03d}.png")
    return len(generated)
