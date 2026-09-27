from __future__ import annotations

import argparse
import json
import os
import site
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def _versions() -> dict[str, str]:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    namespace: dict[str, str] = {}
    exec((PROJECT_ROOT / "research2slides" / "__init__.py").read_text(encoding="utf-8"), namespace)
    return {
        "python_project": pyproject["project"]["version"],
        "python_package": namespace["__version__"],
        "renderer": package["version"],
    }


def run_release_check(output_dir: Path) -> dict[str, object]:
    versions = _versions()
    if len(set(versions.values())) != 1:
        raise RuntimeError(f"Version mismatch: {versions}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    wheel_dir = output_dir / "wheel"
    wheel_dir.mkdir(exist_ok=True)
    build = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        cwd=PROJECT_ROOT,
    )
    if build.returncode != 0:
        raise RuntimeError(build.stderr or build.stdout)
    wheels = sorted(wheel_dir.glob("research2slides-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one wheel, found: {wheels}")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    prompt_members = [name for name in names if "/share/research2slides/prompts/" in name]
    if len(prompt_members) != 8 or "research2slides/cli/app.py" not in names:
        raise RuntimeError("Wheel is missing CLI modules or prompt assets")

    with tempfile.TemporaryDirectory(prefix="research2slides-release-") as temp:
        temp_dir = Path(temp)
        venv_dir = temp_dir / "venv"
        create = _run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            cwd=temp_dir,
        )
        if create.returncode != 0:
            raise RuntimeError(create.stderr or create.stdout)
        python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        install = _run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], cwd=temp_dir)
        if install.returncode != 0:
            raise RuntimeError(install.stderr or install.stdout)
        smoke_env = os.environ.copy()
        smoke_env["PYTHONPATH"] = os.pathsep.join(
            [*site.getsitepackages(), site.getusersitepackages()]
        )
        version = _run(
            [str(python), "-m", "research2slides.cli.app", "version"],
            cwd=temp_dir,
            env=smoke_env,
        )
        doctor = _run(
            [str(python), "-m", "research2slides.cli.app", "doctor"],
            cwd=temp_dir,
            env=smoke_env,
        )
        parse_workspace = temp_dir / "parse-smoke"
        fixture = PROJECT_ROOT / "tests" / "fixtures" / "attention_is_all_you_need"
        parse = _run(
            [
                str(python),
                "-m",
                "research2slides.cli.app",
                "parse",
                str(fixture / "paper.pdf"),
                "--latex",
                str(fixture / "source.zip"),
                "--workspace",
                str(parse_workspace),
            ],
            cwd=temp_dir,
            env=smoke_env,
        )
        failures = {
            name: {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
            for name, result in (("version", version), ("doctor", doctor), ("parse", parse))
            if result.returncode != 0
        }
        if failures:
            raise RuntimeError(f"Installed-wheel smoke test failed: {failures}")
        doctor_payload = json.loads(doctor.stdout)
        parse_payload = json.loads(parse.stdout)

    report = {
        "schema_version": "1.0",
        "status": "pass",
        "version": versions["python_project"],
        "versions": versions,
        "wheel": str(wheel),
        "prompt_assets": len(prompt_members),
        "installed_version": version.stdout.strip(),
        "installed_core_ready": doctor_payload["core_ready"],
        "installed_renderer_ready": doctor_payload["renderer_ready"],
        "parse_smoke_pages": parse_payload["pages"],
    }
    (output_dir / "release_check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and smoke-test a Research2Slides wheel")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_release_check(args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
