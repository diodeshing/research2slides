from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PresentationMode(str, Enum):
    PAPER_READING = "paper-reading"
    OWN_RESEARCH = "own-research"


class LanguageProfile(str, Enum):
    ZH_CN_BILINGUAL_TERMS = "zh_cn_bilingual_terms"


class PresentationLanguageConfig(StrictModel):
    language: Literal["zh-CN"] = "zh-CN"
    terminology_mode: Literal["bilingual"] = "bilingual"
    preserve_source_visual_language: Literal[True] = True
    translate_generic_labels: Literal[True] = True
    translate_speaker_notes: Literal[True] = True


class SourceRole(str, Enum):
    PAPER_PDF = "paper_pdf"
    LATEX_ARCHIVE = "latex_archive"
    LATEX_DIRECTORY = "latex_directory"
    SUPPLEMENT = "supplement"


class AssetKind(str, Enum):
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"


class AssetOrigin(str, Enum):
    LATEX_VECTOR = "latex_vector"
    LATEX_RASTER = "latex_raster"
    PDF_EMBEDDED = "pdf_embedded"
    PDF_CROP = "pdf_crop"


class BoundingBox(StrictModel):
    x0: float
    y0: float
    x1: float
    y1: float
    coordinate_space: Literal["pdf_points", "pixels"] = "pdf_points"

    @model_validator(mode="after")
    def ordered(self) -> "BoundingBox":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bounding box must have positive area")
        return self


class SourceLocator(StrictModel):
    source_type: Literal["paragraph", "figure", "table", "equation"]
    source_id: str
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    figure: str | None = None
    table: str | None = None
    equation: str | None = None
    label: str | None = None
    bbox: BoundingBox | None = None
    excerpt: str = Field(min_length=1)


class SourceFile(StrictModel):
    source_id: str
    role: SourceRole
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class SourceManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    sources: list[SourceFile] = Field(min_length=1)
    combined_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PaperMetadata(StrictModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    language: str | None = None


class Section(StrictModel):
    section_id: str
    title: str
    level: int = Field(ge=1, le=6)
    order: int = Field(ge=0)
    parent_id: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    paragraph_ids: list[str] = Field(default_factory=list)


class Paragraph(StrictModel):
    paragraph_id: str
    text: str = Field(min_length=1)
    section_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    bbox: BoundingBox | None = None
    source: Literal["pdf", "latex"]


class FigureRef(StrictModel):
    figure_id: str
    number: str | None = None
    caption: str | None = None
    label: str | None = None
    source_file: str | None = None
    related_section: str | None = None
    page: int | None = Field(default=None, ge=1)


class TableRef(StrictModel):
    table_id: str
    number: str | None = None
    caption: str | None = None
    label: str | None = None
    latex: str | None = None
    related_section: str | None = None
    page: int | None = Field(default=None, ge=1)


class EquationRef(StrictModel):
    equation_id: str
    number: str | None = None
    label: str | None = None
    latex: str
    related_section: str | None = None
    page: int | None = Field(default=None, ge=1)


class CitationRef(StrictModel):
    citation_id: str
    raw_text: str


class ParserProvenance(StrictModel):
    pdf_backend: str
    latex_backend: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PaperStructure(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    paper_id: str
    metadata: PaperMetadata
    page_count: int = Field(ge=1)
    sections: list[Section] = Field(default_factory=list)
    paragraphs: list[Paragraph] = Field(default_factory=list)
    figures: list[FigureRef] = Field(default_factory=list)
    tables: list[TableRef] = Field(default_factory=list)
    equations: list[EquationRef] = Field(default_factory=list)
    references: list[CitationRef] = Field(default_factory=list)
    provenance: ParserProvenance


class VisualAsset(StrictModel):
    asset_id: str
    type: AssetKind
    origin: AssetOrigin
    priority: int = Field(ge=1, le=4)
    source_path: str
    output_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page: int | None = Field(default=None, ge=1)
    number: str | None = None
    caption: str | None = None
    related_section: str | None = None
    source_label: str | None = None
    media_type: str | None = None


class VisualManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    paper_id: str
    assets: list[VisualAsset] = Field(default_factory=list)
    priority_policy: list[AssetOrigin] = Field(
        default_factory=lambda: [
            AssetOrigin.LATEX_VECTOR,
            AssetOrigin.LATEX_RASTER,
            AssetOrigin.PDF_EMBEDDED,
            AssetOrigin.PDF_CROP,
        ]
    )


class EvidenceNode(StrictModel):
    id: str
    type: Literal[
        "problem", "motivation", "gap", "contribution", "method", "equation",
        "dataset", "metric", "experimental_result", "ablation_result", "limitation", "conclusion"
    ]
    claim: str
    sources: list[SourceLocator] = Field(min_length=1)
    confidence: Literal["low", "medium", "high"]


class EvidenceEdge(StrictModel):
    source_id: str
    target_id: str
    relation: Literal["supports", "contradicts", "motivates", "implements", "validates", "qualifies"]


class EvidenceGraph(StrictModel):
    schema_version: Literal["1.1"] = "1.1"
    paper_id: str
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def graph_integrity(self) -> "EvidenceGraph":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("evidence node IDs must be unique")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source_id not in known or edge.target_id not in known:
                raise ValueError("evidence edges must reference existing nodes")
        return self


InsightCategory = Literal[
    "problem",
    "importance",
    "existing_approaches",
    "gap",
    "central_insight",
    "contributions",
    "method",
    "design_rationale",
    "experiment_findings",
    "ablation_findings",
    "limitations",
    "audience_takeaways",
]


class DraftEvidenceRef(StrictModel):
    source_id: str
    excerpt: str = Field(min_length=1)


class DraftClaim(StrictModel):
    category: InsightCategory
    type: Literal[
        "problem", "motivation", "gap", "contribution", "method", "equation",
        "dataset", "metric", "experimental_result", "ablation_result", "limitation", "conclusion"
    ]
    claim: str = Field(min_length=1)
    source_refs: list[DraftEvidenceRef] = Field(min_length=1)
    confidence: Literal["low", "medium", "high"]


class DraftRelation(StrictModel):
    source_claim_index: int = Field(ge=0)
    target_claim_index: int = Field(ge=0)
    relation: Literal["supports", "contradicts", "motivates", "implements", "validates", "qualifies"]


class AnalysisDraft(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    claims: list[DraftClaim]
    relations: list[DraftRelation] = Field(default_factory=list)


class GroundedAnswer(StrictModel):
    status: Literal["supported", "insufficient_evidence"]
    evidence_ids: list[str]
    note: str


class UnderstandingAnswers(StrictModel):
    problem: GroundedAnswer
    importance: GroundedAnswer
    existing_approaches: GroundedAnswer
    gap: GroundedAnswer
    central_insight: GroundedAnswer
    contributions: GroundedAnswer
    method: GroundedAnswer
    design_rationale: GroundedAnswer
    experiment_findings: GroundedAnswer
    ablation_findings: GroundedAnswer
    limitations: GroundedAnswer
    audience_takeaways: GroundedAnswer


class UnderstandingProvenance(StrictModel):
    provider: str
    model: str
    prompt_version: str
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ScientificUnderstanding(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    paper_id: str
    answers: UnderstandingAnswers
    provenance: UnderstandingProvenance


StorylineRole = Literal[
    "opening",
    "problem",
    "background",
    "existing_approaches",
    "gap",
    "core_insight",
    "contributions",
    "method_overview",
    "method_component",
    "experiments",
    "ablation",
    "analysis",
    "limitations",
    "conclusion",
    "takeaway",
]


class DraftPresentationUnit(StrictModel):
    role: StorylineRole
    section: str = Field(min_length=1)
    question: str = Field(min_length=1)
    main_claim: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    importance: int = Field(ge=1, le=5)
    estimated_seconds: int = Field(ge=20, le=300)
    rationale: str = Field(min_length=1)
    transition_intent: str = Field(min_length=1)


class StorylineDraft(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: PresentationMode
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS
    presentation: PresentationLanguageConfig = Field(default_factory=PresentationLanguageConfig)
    title: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    units: list[DraftPresentationUnit] = Field(min_length=1)


class PresentationUnit(StrictModel):
    unit_id: str
    order: int = Field(ge=1)
    role: StorylineRole
    section: str
    question: str
    main_claim: str
    evidence_ids: list[str] = Field(min_length=1)
    importance: int = Field(ge=1, le=5)
    estimated_seconds: int = Field(ge=20, le=300)
    rationale: str
    transition_intent: str


class PlanProvenance(StrictModel):
    provider: str
    model: str
    prompt_version: str
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CompressionInfo(StrictModel):
    time_budget_seconds: int = Field(gt=0)
    omitted_unit_ids: list[str]


class PresentationPlan(StrictModel):
    schema_version: Literal["1.1"] = "1.1"
    paper_id: str
    mode: PresentationMode
    language: Literal["zh-CN"] = "zh-CN"
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS
    presentation: PresentationLanguageConfig = Field(default_factory=PresentationLanguageConfig)
    title: str
    target_audience: str
    units: list[PresentationUnit] = Field(min_length=1)
    estimated_total_seconds: int = Field(ge=0)
    coverage_gaps: list[str] = Field(default_factory=list)
    compression: CompressionInfo | None = None
    provenance: PlanProvenance

    @model_validator(mode="after")
    def plan_integrity(self) -> "PresentationPlan":
        unit_ids = [unit.unit_id for unit in self.units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("presentation unit IDs must be unique")
        if [unit.order for unit in self.units] != list(range(1, len(self.units) + 1)):
            raise ValueError("presentation unit order must be contiguous and one-based")
        if self.estimated_total_seconds != sum(unit.estimated_seconds for unit in self.units):
            raise ValueError("estimated_total_seconds must equal the sum of unit estimates")
        return self


class SpeakerNotes(StrictModel):
    purpose: str = Field(min_length=1)
    main_message: str = Field(min_length=1)
    script: str = Field(min_length=20)
    visual_guidance: str = Field(min_length=1)
    transition: str = Field(min_length=1)
    estimated_seconds: int = Field(gt=0)


class SlideVisual(StrictModel):
    visual_id: str
    kind: Literal["source_asset", "source_table", "source_equation", "conceptual_diagram"]
    source_ref: str
    role: Literal["primary", "supporting", "background"] = "primary"
    treatment: Literal[
        "original", "crop", "zoom", "highlight", "native_table", "equation", "diagram"
    ]
    caption: str | None = None
    annotations: list[str] = Field(default_factory=list)
    table_column_labels: list[str] | None = None

    @model_validator(mode="after")
    def table_labels_only_for_tables(self) -> "SlideVisual":
        if self.table_column_labels is not None:
            if self.kind != "source_table" or self.treatment != "native_table":
                raise ValueError("table_column_labels require a native source_table visual")
            if not self.table_column_labels or any(not label.strip() for label in self.table_column_labels):
                raise ValueError("table_column_labels must contain non-empty labels")
        return self


SlideLayout = Literal[
    "minimal_text",
    "visual_left_text_right",
    "text_left_visual_right",
    "full_visual",
    "comparison",
    "equation_focus",
    "table_focus",
    "process",
]


class DraftSlide(StrictModel):
    unit_id: str
    purpose: str = Field(min_length=1)
    question: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=110)
    title_kind: Literal["topic", "claim"]
    technical_title: str | None = None
    main_claim: str = Field(min_length=1)
    body: list[str] = Field(min_length=1, max_length=5)
    visuals: list[SlideVisual] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)
    takeaway: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    speaker_notes: SpeakerNotes
    layout: SlideLayout


class SlideSpecDraft(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: PresentationMode
    theme: Literal["conference-minimal", "group-meeting"]
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS
    presentation: PresentationLanguageConfig = Field(default_factory=PresentationLanguageConfig)
    slides: list[DraftSlide] = Field(min_length=1)


class SlideCitation(StrictModel):
    evidence_id: str
    source_ids: list[str] = Field(min_length=1)
    display_text: str = Field(min_length=1)


class Slide(StrictModel):
    slide_id: str
    unit_id: str
    order: int = Field(ge=1)
    section: str
    purpose: str
    question: str
    title: str
    title_kind: Literal["topic", "claim"]
    technical_title: str | None = None
    main_claim: str
    body: list[str] = Field(min_length=1, max_length=5)
    visuals: list[SlideVisual] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)
    takeaway: str
    evidence_ids: list[str] = Field(min_length=1)
    citations: list[SlideCitation] = Field(min_length=1)
    layout: SlideLayout
    speaker_notes: SpeakerNotes


class SlideSpecProvenance(StrictModel):
    provider: str
    model: str
    prompt_version: str
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class SlideSpec(StrictModel):
    schema_version: Literal["1.1"] = "1.1"
    paper_id: str
    mode: PresentationMode
    theme: Literal["conference-minimal", "group-meeting"]
    language: Literal["zh-CN"] = "zh-CN"
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS
    presentation: PresentationLanguageConfig = Field(default_factory=PresentationLanguageConfig)
    title: str
    slides: list[Slide] = Field(min_length=1)
    estimated_total_seconds: int = Field(gt=0)
    provenance: SlideSpecProvenance

    @model_validator(mode="after")
    def slide_spec_integrity(self) -> "SlideSpec":
        if [slide.order for slide in self.slides] != list(range(1, len(self.slides) + 1)):
            raise ValueError("slide order must be contiguous and one-based")
        if len({slide.slide_id for slide in self.slides}) != len(self.slides):
            raise ValueError("slide IDs must be unique")
        if len({slide.unit_id for slide in self.slides}) != len(self.slides):
            raise ValueError("each presentation unit may map to only one slide")
        if self.estimated_total_seconds != sum(
            slide.speaker_notes.estimated_seconds for slide in self.slides
        ):
            raise ValueError("estimated_total_seconds must equal speaker-note estimates")
        return self


class SemanticDependency(StrictModel):
    concept: str = Field(min_length=1)
    prerequisite_slide_ids: list[str] = Field(default_factory=list)
    required: bool = True
    rationale: str = Field(min_length=1)


class SemanticSlideEvaluation(StrictModel):
    slide_id: str = Field(min_length=1)
    claim_evidence: Literal[
        "entailed", "partially_supported", "unsupported", "insufficient_evidence"
    ]
    claim_evidence_rationale: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    claim_strength: Literal["calibrated", "overstated", "understated", "not_applicable"]
    claim_strength_rationale: str = Field(min_length=1)
    dependencies: list[SemanticDependency] = Field(default_factory=list)


class SemanticQADraft(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    evaluations: list[SemanticSlideEvaluation] = Field(min_length=1)

    @model_validator(mode="after")
    def evaluation_ids_are_unique(self) -> "SemanticQADraft":
        slide_ids = [evaluation.slide_id for evaluation in self.evaluations]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("semantic QA slide IDs must be unique")
        return self


class SemanticQAProvenance(StrictModel):
    provider: str
    model: str
    prompt_version: str
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class SemanticQAResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    paper_id: str
    evaluations: list[SemanticSlideEvaluation] = Field(min_length=1)
    provenance: SemanticQAProvenance

    @model_validator(mode="after")
    def evaluation_ids_are_unique(self) -> "SemanticQAResult":
        slide_ids = [evaluation.slide_id for evaluation in self.evaluations]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("semantic QA slide IDs must be unique")
        return self


class QACategory(str, Enum):
    FACTUAL = "factual"
    STORYLINE = "storyline"
    VISUAL = "visual"
    PRESENTATION = "presentation"


class QASeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class QAStatus(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"


class Repairability(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    NONE = "none"


class QAIssue(StrictModel):
    issue_id: str
    category: QACategory
    code: str
    severity: QASeverity
    message: str
    slide_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    field_path: str | None = None
    repairability: Repairability = Repairability.MANUAL
    suggested_action: str


class QACategoryResult(StrictModel):
    category: QACategory
    status: QAStatus
    checks_run: int = Field(ge=1)
    issue_ids: list[str] = Field(default_factory=list)


class QAArtifactPaths(StrictModel):
    pptx: str
    pdf: str | None = None
    preview_dir: str | None = None
    targeted_review_pptx: str | None = None


class QARepairAction(StrictModel):
    action_id: str
    issue_id: str
    slide_id: str
    field_path: str
    before: str
    after: str
    evidence_preserved: Literal[True] = True


class QAIteration(StrictModel):
    iteration: int = Field(ge=1)
    issue_count_before: int = Field(ge=0)
    issue_count_after: int = Field(ge=0)
    repaired_slide_numbers: list[int] = Field(default_factory=list)
    actions: list[QARepairAction] = Field(default_factory=list)


class QAProvenance(StrictModel):
    qa_version: str
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    render_backend: str
    checks: list[str] = Field(min_length=1)


class QualityReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    paper_id: str
    mode: PresentationMode
    theme: Literal["conference-minimal", "group-meeting"]
    status: QAStatus
    slide_count: int = Field(gt=0)
    categories: list[QACategoryResult] = Field(min_length=4, max_length=4)
    issues: list[QAIssue] = Field(default_factory=list)
    repairs: list[QAIteration] = Field(default_factory=list)
    artifacts: QAArtifactPaths
    manual_review_required: bool
    limitations: list[str] = Field(default_factory=list)
    provenance: QAProvenance

    @model_validator(mode="after")
    def report_integrity(self) -> "QualityReport":
        issue_ids = [issue.issue_id for issue in self.issues]
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("QA issue IDs must be unique")
        category_names = [result.category for result in self.categories]
        if set(category_names) != set(QACategory):
            raise ValueError("quality report must contain each QA category exactly once")
        known_issues = set(issue_ids)
        for result in self.categories:
            if not set(result.issue_ids).issubset(known_issues):
                raise ValueError("category result references an unknown QA issue")
        expected = QAStatus.PASS
        if any(issue.severity == QASeverity.ERROR for issue in self.issues):
            expected = QAStatus.FAIL
        elif any(issue.severity == QASeverity.WARNING for issue in self.issues):
            expected = QAStatus.PASS_WITH_WARNINGS
        if self.status != expected:
            raise ValueError("quality report status does not match issue severity")
        return self
