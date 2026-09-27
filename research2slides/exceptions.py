class Research2SlidesError(Exception):
    """Base exception for user-facing pipeline failures."""


class InputError(Research2SlidesError):
    """Raised when an input is missing, unsafe, or unsupported."""


class ParseError(Research2SlidesError):
    """Raised when a source cannot be parsed into the unified model."""


class ArtifactError(Research2SlidesError):
    """Raised when a persisted artifact is invalid or inconsistent."""


class ProviderError(Research2SlidesError):
    """Raised when an understanding provider fails or returns invalid data."""


class EvidenceError(Research2SlidesError):
    """Raised when a claim cannot be traced to the supplied paper artifacts."""


class PlanningError(Research2SlidesError):
    """Raised when a presentation plan violates evidence or storyline constraints."""


class SlideSpecError(Research2SlidesError):
    """Raised when a slide specification violates plan, evidence, or visual constraints."""


class RenderError(Research2SlidesError):
    """Raised when the TypeScript renderer cannot build a PowerPoint artifact."""


class QualityAssuranceError(Research2SlidesError):
    """Raised when Phase 6 QA cannot inspect, report, or safely repair a deck."""
