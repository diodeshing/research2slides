import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_version_and_doctor_commands() -> None:
    version = subprocess.run(
        [sys.executable, "-m", "research2slides.cli.app", "version"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    doctor = subprocess.run(
        [sys.executable, "-m", "research2slides.cli.app", "doctor", "--require-renderer"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert version.returncode == 0
    assert version.stdout.strip() == "0.2.0"
    assert doctor.returncode == 0
    payload = json.loads(doctor.stdout)
    assert payload["core_ready"] is True
    assert payload["renderer_ready"] is True


def test_parse_command_emits_machine_readable_summary(tmp_path: Path) -> None:
    fixture = PROJECT_ROOT / "tests" / "fixtures" / "attention_is_all_you_need"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "parse",
            str(fixture / "paper.pdf"),
            "--latex",
            str(fixture / "source.zip"),
            "--workspace",
            str(tmp_path / "workspace"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "generated"
    assert payload["sections"] >= 3
    assert payload["assets"] >= 1


def test_understand_command_uses_offline_draft(tmp_path: Path) -> None:
    fixture = PROJECT_ROOT / "tests" / "fixtures" / "attention_is_all_you_need"
    workspace = tmp_path / "workspace"
    parse = subprocess.run(
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "parse",
            str(fixture / "paper.pdf"),
            "--latex",
            str(fixture / "source.zip"),
            "--workspace",
            str(workspace),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert parse.returncode == 0, parse.stderr
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "understand",
            str(workspace),
            "--draft",
            str(fixture / "analysis_draft.json"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "generated"
    assert payload["evidence_nodes"] == 6
    assert payload["provider"] == "json-draft"


def test_plan_command_keeps_full_plan_and_compresses_selection(tmp_path: Path) -> None:
    fixture = PROJECT_ROOT / "tests" / "fixtures" / "attention_is_all_you_need"
    workspace = tmp_path / "workspace"
    commands = [
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "parse",
            str(fixture / "paper.pdf"),
            "--latex",
            str(fixture / "source.zip"),
            "--workspace",
            str(workspace),
        ],
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "understand",
            str(workspace),
            "--draft",
            str(fixture / "analysis_draft.json"),
        ],
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "plan",
            str(workspace),
            "--mode",
            "paper-reading",
            "--draft",
            str(fixture / "storyline_paper_reading.json"),
            "--time-minutes",
            "5.75",
        ],
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "spec",
            str(workspace),
            "--draft",
            str(fixture / "slide_spec_paper_reading.json"),
        ],
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "render",
            str(workspace),
        ],
    ]
    results = [
        subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        for command in commands
    ]
    assert all(result.returncode == 0 for result in results), "\n".join(result.stderr for result in results)
    payload = json.loads(results[-3].stdout)
    assert payload["full_units"] == 7
    assert payload["selected_units"] == 6
    assert payload["compressed"] is True
    assert (workspace / "data" / "presentation_plan.full.json").is_file()
    assert (workspace / "data" / "presentation_plan.json").is_file()
    spec_payload = json.loads(results[-2].stdout)
    assert spec_payload["slides"] == 6
    assert spec_payload["theme"] == "group-meeting"
    assert (workspace / "data" / "slide_spec.json").is_file()
    assert (workspace / "speaker_notes.md").is_file()
    assert (workspace / "presentation_outline.md").is_file()
    render_payload = json.loads(results[-1].stdout)
    assert render_payload["status"] == "generated"
    assert render_payload["theme"] == "group-meeting"
    assert len(render_payload["slides"]) == 6
    assert (workspace / "output" / "presentation.pptx").is_file()


def test_build_command_runs_offline_pipeline_and_packages_delivery(tmp_path: Path) -> None:
    fixture = PROJECT_ROOT / "tests" / "fixtures" / "attention_is_all_you_need"
    workspace = tmp_path / "build-workspace"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research2slides.cli.app",
            "build",
            str(fixture / "paper.pdf"),
            "--latex",
            str(fixture / "source.zip"),
            "--workspace",
            str(workspace),
            "--analysis-draft",
            str(fixture / "analysis_draft.json"),
            "--storyline-draft",
            str(fixture / "storyline_paper_reading.json"),
            "--slide-spec-draft",
            str(fixture / "slide_spec_paper_reading.json"),
            "--semantic-qa-draft",
            str(PROJECT_ROOT / "tests" / "fixtures" / "phase9" / "semantic_qa_valid.json"),
            "--time-minutes",
            "5.75",
            "--no-render-qa",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert all(status == "completed" for status in payload["steps"].values())
    assert (workspace / "build_checkpoint.json").is_file()
    assert (workspace / "delivery" / "presentation.pptx").is_file()
    assert (workspace / "delivery" / "speaker_notes.md").is_file()
    assert (workspace / "delivery" / "quality_report.md").is_file()
    assert (workspace / "delivery" / "semantic_qa.json").is_file()
