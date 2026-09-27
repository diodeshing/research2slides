from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_bundle_templates_are_offline_and_renderer_aware() -> None:
    templates = PROJECT_ROOT / "packaging" / "local_bundle"
    install = (templates / "install.ps1").read_text(encoding="utf-8")
    runner = (templates / "run.ps1").read_text(encoding="utf-8")
    verify = (templates / "verify.ps1").read_text(encoding="utf-8")
    assert "--no-index" in install
    assert "RESEARCH2SLIDES_RENDERER_ROOT" in runner
    assert "--no-render-qa" in verify
    assert "--semantic-qa-draft" in verify
    builder = (PROJECT_ROOT / "scripts" / "build_local_bundle.py").read_text(encoding="utf-8")
    assert 'PROJECT_ROOT / "themes"' in builder


def test_runtime_lock_is_fully_pinned() -> None:
    lines = [
        line.strip()
        for line in (PROJECT_ROOT / "requirements-runtime-lock.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert len(lines) >= 20
    assert all("==" in line for line in lines)
