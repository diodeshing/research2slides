from pathlib import Path
from io import BytesIO
from tarfile import TarInfo, open as open_tar
from zipfile import ZipFile

import pytest

from research2slides.exceptions import InputError
from research2slides.ingestion.latex import materialize_latex


def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("../escape.tex", "not allowed")
    with pytest.raises(InputError, match="Unsafe path"):
        with materialize_latex(archive):
            pass


def test_tar_archive_is_materialized(tmp_path: Path) -> None:
    archive = tmp_path / "source.tar.gz"
    payload = b"\\documentclass{article}\\begin{document}ok\\end{document}"
    with open_tar(archive, "w:gz") as output:
        info = TarInfo("paper/main.tex")
        info.size = len(payload)
        output.addfile(info, BytesIO(payload))
    with materialize_latex(archive) as root:
        assert (root / "paper" / "main.tex").read_bytes() == payload


def test_tar_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar"
    payload = b"not allowed"
    with open_tar(archive, "w") as output:
        info = TarInfo("../escape.tex")
        info.size = len(payload)
        output.addfile(info, BytesIO(payload))
    with pytest.raises(InputError, match="Unsafe path"):
        with materialize_latex(archive):
            pass


def test_tar_links_are_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe-link.tar"
    with open_tar(archive, "w") as output:
        info = TarInfo("paper/main.tex")
        info.type = b"2"
        info.linkname = "../outside.tex"
        output.addfile(info)
    with pytest.raises(InputError, match="Link entries"):
        with materialize_latex(archive):
            pass
