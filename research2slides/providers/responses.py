from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from research2slides.exceptions import ProviderError


OutputT = TypeVar("OutputT", bound=BaseModel)
Transport = Callable[[dict[str, Any]], dict[str, Any]]


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Pydantic schema for strict Structured Outputs."""

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            properties = value.get("properties")
            if isinstance(properties, dict):
                value["required"] = list(properties)
                value["additionalProperties"] = False
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(schema)
    return schema


class StructuredResponsesClient:
    def __init__(
        self,
        model: str,
        reasoning_effort: str,
        base_url: str,
        api_key_env: str,
        timeout_seconds: int = 180,
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def cache_key(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "base_url": self.base_url,
                "prompt": prompt,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def generate(
        self,
        prompt: str,
        context: str,
        output_type: type[OutputT],
        schema_name: str,
    ) -> OutputT:
        payload: dict[str, Any] = {
            "model": self.model,
            "reasoning": {"effort": self.reasoning_effort},
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": strict_schema(output_type.model_json_schema()),
                }
            },
            "store": False,
        }
        response = self._transport(payload) if self._transport else self._post(payload)
        output_text = self.extract_output_text(response)
        try:
            return output_type.model_validate_json(output_text)
        except ValidationError as exc:
            raise ProviderError(f"Provider returned invalid structured output: {exc}") from exc

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ProviderError(f"Missing API key environment variable: {self.api_key_env}")
        request = urllib.request.Request(
            f"{self.base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderError(f"Responses API returned HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Responses API request failed: {exc}") from exc

    @staticmethod
    def extract_output_text(response: dict[str, Any]) -> str:
        if response.get("status") not in (None, "completed"):
            raise ProviderError(f"Provider response did not complete: {response.get('status')}")
        if isinstance(response.get("output_text"), str):
            return response["output_text"]
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise ProviderError(f"Provider refused the request: {content.get('refusal', '')}")
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise ProviderError("Provider response did not contain structured output text")

