from __future__ import annotations

import stat
import tarfile
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Iterator

from research2slides.exceptions import InputError


def _validate_member(info: zipfile.ZipInfo) -> PurePosixPath:
    raw = info.filename.replace("\\", "/")
    member = PurePosixPath(raw)
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise InputError(f"Unsafe path in LaTeX archive: {info.filename}")
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise InputError(f"Symlink entries are not allowed in LaTeX archive: {info.filename}")
    return member


def _validate_tar_member(info: tarfile.TarInfo) -> PurePosixPath:
    raw = info.name.replace("\\", "/")
    member = PurePosixPath(raw)
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise InputError(f"Unsafe path in LaTeX archive: {info.name}")
    if info.issym() or info.islnk():
        raise InputError(f"Link entries are not allowed in LaTeX archive: {info.name}")
    if not (info.isdir() or info.isfile()):
        raise InputError(f"Unsupported entry in LaTeX archive: {info.name}")
    return member


def is_latex_archive(source: Path) -> bool:
    name = source.name.lower()
    return name.endswith((".zip", ".tar", ".tar.gz", ".tgz"))


@contextmanager
def materialize_latex(source: Path) -> Iterator[Path]:
    source = source.resolve()
    if source.is_dir():
        yield source
        return
    if not source.is_file() or not is_latex_archive(source):
        raise InputError(f"LaTeX source must be a directory, ZIP, TAR, TAR.GZ, or TGZ: {source}")

    with tempfile.TemporaryDirectory(prefix="research2slides-latex-") as temp:
        root = Path(temp)
        if source.suffix.lower() == ".zip":
            with zipfile.ZipFile(source) as archive:
                members = [(info, _validate_member(info)) for info in archive.infolist()]
                for info, member in members:
                    target = root.joinpath(*member.parts)
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as src, target.open("wb") as dst:
                        while chunk := src.read(1024 * 1024):
                            dst.write(chunk)
        else:
            try:
                with tarfile.open(source, mode="r:*") as archive:
                    members = [(info, _validate_tar_member(info)) for info in archive.getmembers()]
                    for info, member in members:
                        target = root.joinpath(*member.parts)
                        if info.isdir():
                            target.mkdir(parents=True, exist_ok=True)
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        src = archive.extractfile(info)
                        if src is None:
                            raise InputError(f"Could not read LaTeX archive entry: {info.name}")
                        with src, target.open("wb") as dst:
                            while chunk := src.read(1024 * 1024):
                                dst.write(chunk)
            except tarfile.TarError as exc:
                raise InputError(f"Invalid TAR LaTeX archive: {source}") from exc
        yield root


def find_main_tex(root: Path) -> Path:
    candidates = sorted(root.rglob("*.tex"))
    if not candidates:
        raise InputError(f"No .tex file found in {root}")
    documents = []
    for candidate in candidates:
        text = candidate.read_text(encoding="utf-8", errors="replace")
        if "\\documentclass" in text and "\\begin{document}" in text:
            documents.append(candidate)
    return sorted(documents or candidates, key=lambda item: (len(item.parts), item.as_posix()))[0]
