from __future__ import annotations

import hashlib
from pathlib import Path

from research2slides.artifacts import read_model, write_model
from research2slides.models import (
    EvidenceGraph,
    LanguageProfile,
    PlanProvenance,
    PresentationMode,
    PresentationPlan,
    ScientificUnderstanding,
)
from research2slides.planning.compression import compress_plan
from research2slides.planning.context import build_storyline_context
from research2slides.planning.providers import PROMPT_VERSION, StorylineProvider
from research2slides.planning.storyline import build_presentation_plan


def _fingerprint(
    data_dir: Path,
    provider: StorylineProvider,
    mode: PresentationMode,
    time_budget_seconds: int | None,
    language_profile: LanguageProfile,
) -> str:
    digest = hashlib.sha256()
    for name in ("scientific_understanding.json", "evidence_graph.json"):
        digest.update(name.encode("utf-8"))
        digest.update((data_dir / name).read_bytes())
    digest.update(provider.cache_key().encode("ascii"))
    digest.update(mode.value.encode("ascii"))
    digest.update(str(time_budget_seconds).encode("ascii"))
    digest.update(language_profile.value.encode("ascii"))
    return digest.hexdigest()


def run_planning(
    workspace: Path,
    provider: StorylineProvider,
    mode: PresentationMode,
    time_budget_seconds: int | None = None,
    force: bool = False,
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS,
) -> tuple[PresentationPlan, PresentationPlan, bool]:
    data_dir = workspace.resolve() / "data"
    understanding = read_model(data_dir / "scientific_understanding.json", ScientificUnderstanding)
    graph = read_model(data_dir / "evidence_graph.json", EvidenceGraph)
    fingerprint = _fingerprint(data_dir, provider, mode, time_budget_seconds, language_profile)
    full_path = data_dir / "presentation_plan.full.json"
    plan_path = data_dir / "presentation_plan.json"

    if not force and full_path.is_file() and plan_path.is_file():
        full = read_model(full_path, PresentationPlan)
        plan = read_model(plan_path, PresentationPlan)
        if (
            plan.provenance.input_fingerprint == fingerprint
            and full.provenance.input_fingerprint == fingerprint
            and plan.mode == mode
            and plan.paper_id == graph.paper_id
            and plan.language_profile == language_profile
        ):
            return plan, full, True

    context = build_storyline_context(understanding, graph, mode, language_profile)
    draft = provider.plan(context)
    provenance = PlanProvenance(
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        input_fingerprint=fingerprint,
    )
    full = build_presentation_plan(
        graph.paper_id,
        draft,
        graph,
        mode,
        provenance,
        language_profile=language_profile,
    )
    plan = compress_plan(full, time_budget_seconds) if time_budget_seconds else full.model_copy(deep=True)
    write_model(full_path, full)
    write_model(plan_path, plan)
    return plan, full, False
