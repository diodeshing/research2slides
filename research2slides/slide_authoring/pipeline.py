from __future__ import annotations

import hashlib
from pathlib import Path

from research2slides.artifacts import read_model, write_model, write_text
from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    PresentationPlan,
    SlideSpec,
    SlideSpecProvenance,
    VisualManifest,
)
from research2slides.narration.speaker_notes import render_presentation_outline, render_speaker_notes
from research2slides.slide_authoring.builder import build_slide_spec
from research2slides.slide_authoring.context import build_slide_context
from research2slides.slide_authoring.providers import PROMPT_VERSION, SlideSpecProvider


def _fingerprint(data_dir: Path, provider: SlideSpecProvider, theme: str) -> str:
    digest = hashlib.sha256()
    for name in (
        "presentation_plan.json",
        "evidence_graph.json",
        "paper_structure.json",
        "visual_manifest.json",
    ):
        digest.update(name.encode("utf-8"))
        digest.update((data_dir / name).read_bytes())
    digest.update(provider.cache_key().encode("ascii"))
    digest.update(theme.encode("ascii"))
    return digest.hexdigest()


def run_slide_authoring(
    workspace: Path,
    provider: SlideSpecProvider,
    theme: str,
    force: bool = False,
) -> tuple[SlideSpec, bool]:
    workspace = workspace.resolve()
    data_dir = workspace / "data"
    plan = read_model(data_dir / "presentation_plan.json", PresentationPlan)
    graph = read_model(data_dir / "evidence_graph.json", EvidenceGraph)
    paper = read_model(data_dir / "paper_structure.json", PaperStructure)
    visuals = read_model(data_dir / "visual_manifest.json", VisualManifest)
    fingerprint = _fingerprint(data_dir, provider, theme)
    spec_path = data_dir / "slide_spec.json"

    if not force and spec_path.is_file():
        spec = read_model(spec_path, SlideSpec)
        if spec.provenance.input_fingerprint == fingerprint and spec.theme == theme:
            write_text(workspace / "speaker_notes.md", render_speaker_notes(spec))
            write_text(workspace / "presentation_outline.md", render_presentation_outline(spec))
            return spec, True

    context = build_slide_context(plan, graph, paper, visuals, theme)
    draft = provider.author(context)
    provenance = SlideSpecProvenance(
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        input_fingerprint=fingerprint,
    )
    spec = build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)
    write_model(spec_path, spec)
    write_text(workspace / "speaker_notes.md", render_speaker_notes(spec))
    write_text(workspace / "presentation_outline.md", render_presentation_outline(spec))
    return spec, False

