from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from research2slides.exceptions import ProviderError
from research2slides.models import StorylineDraft
from research2slides.providers.responses import StructuredResponsesClient, Transport


PROMPT_VERSION = "storyline-v2-zh-cn-bilingual-terms"


class StorylineProvider(Protocol):
    provider_name: str
    model_name: str

    def cache_key(self) -> str: ...

    def plan(self, context: str) -> StorylineDraft: ...


class JsonStorylineProvider:
    provider_name = "json-storyline"
    model_name = "offline-fixture"

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def cache_key(self) -> str:
        try:
            return hashlib.sha256(self.path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ProviderError(f"Unable to read storyline draft {self.path}: {exc}") from exc

    def plan(self, context: str) -> StorylineDraft:
        del context
        try:
            return StorylineDraft.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise ProviderError(f"Invalid storyline draft {self.path}: {exc}") from exc


class OpenAIStorylineProvider:
    provider_name = "openai-responses"

    def __init__(
        self,
        prompt: str,
        model: str = "gpt-5.6-sol",
        reasoning_effort: str = "high",
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        timeout_seconds: int = 180,
        transport: Transport | None = None,
    ) -> None:
        self.prompt = prompt
        self.model_name = model
        self._client = StructuredResponsesClient(
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )

    def cache_key(self) -> str:
        return self._client.cache_key(self.prompt)

    def plan(self, context: str) -> StorylineDraft:
        return self._client.generate(
            self.prompt,
            context,
            StorylineDraft,
            "research2slides_storyline_draft",
        )
