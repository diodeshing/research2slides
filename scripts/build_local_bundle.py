from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
BUNDLE_NAME = f"research2slides-{VERSION}-windows-local"


def _copy(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_local_bundle(output_dir: Path, wheel_cache: Path) -> dict[str, object]:
    output_dir = output_dir.resolve()
    wheel_cache = wheel_cache.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    wheel_cache.mkdir(parents=True, exist_ok=True)
    project_wheel = (
        PROJECT_ROOT
        / "examples"
        / "phase11"
        / "output"
        / "wheel"
        / f"research2slides-{VERSION}-py3-none-any.whl"
    )
    required = [
        project_wheel,
        PROJECT_ROOT / "node_modules",
        PROJECT_ROOT / "renderer" / "dist",
        PROJECT_ROOT / "renderer" / "src",
        PROJECT_ROOT / "renderer" / "tsconfig.json",
        PROJECT_ROOT / "themes",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Local bundle inputs are missing: {missing}")

    download = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            str(wheel_cache),
            "--requirement",
            str(PROJECT_ROOT / "requirements-runtime-lock.txt"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if download.returncode != 0:
        raise RuntimeError(download.stderr or download.stdout)

    with tempfile.TemporaryDirectory(prefix="research2slides-bundle-") as temp:
        root = Path(temp) / BUNDLE_NAME
        wheel_dir = root / "python_wheels"
        wheel_dir.mkdir(parents=True)
        for wheel in wheel_cache.glob("*.whl"):
            shutil.copy2(wheel, wheel_dir / wheel.name)
        shutil.copy2(project_wheel, wheel_dir / project_wheel.name)

        renderer = root / "renderer_runtime"
        _copy(PROJECT_ROOT / "node_modules", renderer / "node_modules")
        _copy(PROJECT_ROOT / "renderer" / "dist", renderer / "renderer" / "dist")
        _copy(PROJECT_ROOT / "renderer" / "src", renderer / "renderer" / "src")
        _copy(PROJECT_ROOT / "renderer" / "tsconfig.json", renderer / "renderer" / "tsconfig.json")
        _copy(PROJECT_ROOT / "package.json", renderer / "package.json")
        _copy(PROJECT_ROOT / "package-lock.json", renderer / "package-lock.json")
        _copy(PROJECT_ROOT / "themes", renderer / "themes")
        _copy(PROJECT_ROOT / "LICENSE", root / "LICENSE")

        templates = PROJECT_ROOT / "packaging" / "local_bundle"
        for name in ("install.ps1", "run.ps1", "verify.ps1", "README_LOCAL.md"):
            _copy(templates / name, root / name)

        fixture = PROJECT_ROOT / "tests" / "fixtures" / "attention_is_all_you_need"
        sample_files = {
            fixture / "paper.pdf": "paper.pdf",
            fixture / "source.zip": "source.zip",
            fixture / "analysis_draft.json": "analysis_draft.json",
            fixture / "storyline_paper_reading.json": "storyline_draft.json",
            fixture / "slide_spec_paper_reading.json": "slide_spec_draft.json",
            PROJECT_ROOT / "tests" / "fixtures" / "phase9" / "semantic_qa_valid.json": "semantic_qa_draft.json",
        }
        for source, name in sample_files.items():
            _copy(source, root / "sample" / name)

        files = sorted(path for path in root.rglob("*") if path.is_file())
        checksum_lines = [f"{_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files]
        (root / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

        zip_path = output_dir / f"{BUNDLE_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                archive.write(path, Path(BUNDLE_NAME) / path.relative_to(root))

    report = {
        "schema_version": "1.0",
        "status": "built",
        "version": VERSION,
        "bundle": str(zip_path),
        "sha256": _sha256(zip_path),
        "bytes": zip_path.stat().st_size,
        "python_dependency_wheels": len(list(wheel_cache.glob("*.whl"))),
        "node_modules_included": True,
        "offline_install": True,
    }
    (output_dir / "local_bundle_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline Windows local bundle")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel-cache", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_local_bundle(args.output, args.wheel_cache), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
