from __future__ import annotations

import json
from pathlib import Path

import pytest

from research2slides.exceptions import RenderError
from research2slides.orchestration import BUILD_STEPS, BuildOptions, run_build


class DummyProvider:
    def __init__(self, key: str) -> None:
        self.key = key

    def cache_key(self) -> str:
        return self.key


def _write(path: Path, content: str = "ok") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _handlers(workspace: Path, calls: list[str], fail_render: bool = False):
    data = workspace / "data"
    output = workspace / "output"
    delivery = workspace / "delivery"

    def handler(name: str, files: list[Path]):
        def run() -> dict[str, object]:
            calls.append(name)
            if name == "render" and fail_render:
                raise RenderError("simulated renderer failure")
            for file in files:
                _write(file)
            return {"stage": name}

        return run

    return {
        "parse": handler(
            "parse",
            [data / "paper_structure.json", data / "visual_manifest.json", data / "source_manifest.json"],
        ),
        "understand": handler(
            "understand", [data / "scientific_understanding.json", data / "evidence_graph.json"]
        ),
        "plan": handler(
            "plan", [data / "presentation_plan.full.json", data / "presentation_plan.json"]
        ),
        "spec": handler(
            "spec",
            [data / "slide_spec.json", workspace / "speaker_notes.md", workspace / "presentation_outline.md"],
        ),
        "render": handler("render", [output / "presentation.pptx"]),
        "qa": handler("qa", [output / "quality_report.json", output / "quality_report.md"]),
        "package": handler(
            "package",
            [
                delivery / "presentation.pptx",
                delivery / "speaker_notes.md",
                delivery / "presentation_outline.md",
                delivery / "quality_report.md",
            ],
        ),
    }


def test_build_checkpoint_resumes_from_failed_stage(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"paper")
    workspace = tmp_path / "workspace"
    providers = [DummyProvider("analysis"), DummyProvider("storyline"), DummyProvider("slides")]
    options = BuildOptions(render_qa=False)
    first_calls: list[str] = []

    with pytest.raises(RenderError, match="simulated renderer failure"):
        run_build(
            pdf,
            workspace,
            latex=None,
            understanding_provider=providers[0],
            storyline_provider=providers[1],
            slide_spec_provider=providers[2],
            options=options,
            handlers=_handlers(workspace, first_calls, fail_render=True),
        )

    failed = json.loads((workspace / "build_checkpoint.json").read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["failed_step"] == "render"
    assert first_calls == list(BUILD_STEPS[:5])

    resumed_calls: list[str] = []
    result = run_build(
        pdf,
        workspace,
        latex=None,
        understanding_provider=providers[0],
        storyline_provider=providers[1],
        slide_spec_provider=providers[2],
        options=options,
        handlers=_handlers(workspace, resumed_calls),
    )

    assert result["status"] == "completed"
    assert resumed_calls == ["render", "qa", "package"]
    completed = json.loads((workspace / "build_checkpoint.json").read_text(encoding="utf-8"))
    assert completed["status"] == "completed"
    assert all(completed["steps"][name]["status"] == "completed" for name in BUILD_STEPS)
    assert (workspace / "delivery" / "build_checkpoint.json").is_file()
