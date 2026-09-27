from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=script.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def validate_local_bundle(bundle: Path, report_path: Path) -> dict[str, object]:
    bundle = bundle.resolve()
    with tempfile.TemporaryDirectory(prefix="research2slides-local-validate-") as temp:
        temp_dir = Path(temp).resolve()
        with zipfile.ZipFile(bundle) as archive:
            for member in archive.infolist():
                target = (temp_dir / member.filename).resolve()
                if temp_dir not in target.parents and target != temp_dir:
                    raise RuntimeError(f"Unsafe bundle entry: {member.filename}")
            archive.extractall(temp_dir)
        roots = [path for path in temp_dir.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise RuntimeError(f"Expected one bundle root, found: {roots}")
        root = roots[0]
        checksum_file = root / "SHA256SUMS.txt"
        checked = 0
        for line in checksum_file.read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            target = root / Path(relative)
            if not target.is_file() or _sha256(target) != expected:
                raise RuntimeError(f"Checksum mismatch: {relative}")
            checked += 1
        install = _run(root / "install.ps1")
        if install.returncode != 0:
            raise RuntimeError(f"Offline install failed: {install.stderr or install.stdout}")
        verify = _run(root / "verify.ps1")
        if verify.returncode != 0:
            raise RuntimeError(f"Bundle verification failed: {verify.stderr or verify.stdout}")
        delivery = root / "smoke_workspace" / "delivery"
        required = [
            delivery / "presentation.pptx",
            delivery / "quality_report.md",
            delivery / "semantic_qa.json",
        ]
        if not all(path.is_file() for path in required):
            raise RuntimeError("Bundle smoke test did not create the expected delivery artifacts")
        report = {
            "schema_version": "1.0",
            "status": "pass",
            "bundle": str(bundle),
            "bundle_sha256": _sha256(bundle),
            "checksums_verified": checked,
            "offline_install": True,
            "doctor_renderer_ready": True,
            "end_to_end_delivery": True,
        }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract, install, and smoke-test a local bundle")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate_local_bundle(args.bundle, args.report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
