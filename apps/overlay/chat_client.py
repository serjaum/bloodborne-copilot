"""OpenAI-compatible chat completions client and Bloodborne context prompt."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from apps.overlay.providers import PROVIDERS


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

QUICK_PROMPTS = {
    "Build": (
        "Review my build using the loaded save snapshot. Give one concise, spoiler-light "
        "suggestion. Ask which weapon I use if that matters; do not assume it from the snapshot."
    ),
    "Boss": (
        "Help me prepare for a boss. Ask which boss I mean if I have not named it, "
        "then give spoiler-light, actionable advice."
    ),
    "Next step": (
        "Help me decide what to do next. Ask for my current area and goal first; "
        "do not infer my current location or progression from the save snapshot."
    ),
}


@dataclass(frozen=True)
class ProviderSettings:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: str = ""
    provider: str = "openai"

    @classmethod
    def from_environment(cls) -> "ProviderSettings":
        provider = os.environ.get("COPILOT_PROVIDER", "").strip().lower()
        if not provider:
            provider = "custom" if "OPENAI_BASE_URL" in os.environ else "openai"
        if provider == "opencode_go":
            preset = PROVIDERS[provider]
            return cls(
                base_url=preset.base_url,
                model=os.environ.get("OPENCODE_GO_MODEL", preset.default_model).strip(),
                api_key=os.environ.get("OPENCODE_GO_API_KEY", "").strip(),
                provider=provider,
            )
        return cls(
            base_url=os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip(),
            model=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip(),
            api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
            provider=provider,
        )


def _format_http_error(exc: HTTPError) -> str:
    try:
        raw_body = exc.read()
    finally:
        exc.close()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    nested = payload.get("error")
    nested = nested if isinstance(nested, dict) else {}
    error_type = payload.get("type") or nested.get("type") or payload.get("code")
    message = payload.get("message") or nested.get("message") or payload.get("detail")
    detail_parts = [str(part) for part in (error_type, message) if part]
    suffix = f": {' — '.join(detail_parts)}" if detail_parts else ""
    return f"Provider returned HTTP {exc.code}{suffix}"


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 45.0,
        models_url: str | None = None,
        extra_headers: dict[str, str] | None = None,
        api_family: str = "chat_completions",
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.model = model.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.models_url = models_url.strip().rstrip("/") if models_url else ""
        self.extra_headers = dict(extra_headers or {})
        self.api_family = api_family

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.base_url.startswith(("https://", "http://")):
            raise ValueError("Provider URL must start with http:// or https://")
        if not self.model:
            raise ValueError("Enter a model name in Settings")

        if self.api_family not in {"chat_completions", "responses"}:
            raise ValueError(f"Unsupported provider API family: {self.api_family}")
        route = "responses" if self.api_family == "responses" else "chat/completions"
        endpoint = (
            self.base_url
            if self.base_url.endswith(f"/{route}")
            else f"{self.base_url}/{route}"
        )
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.api_family == "responses":
            input_messages = [
                {
                    "role": message.get("role", "user"),
                    "content": message.get("content", ""),
                }
                for message in messages
            ]
            request_payload = {"model": self.model, "input": input_messages}
        else:
            request_payload = {"model": self.model, "messages": messages}
        body = json.dumps(request_payload).encode("utf-8")
        request = Request(endpoint, data=body, headers=headers, method="POST")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload: Any = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(_format_http_error(exc)) from None
        except URLError as exc:
            raise RuntimeError(f"Could not reach provider: {exc.reason}") from None
        except TimeoutError:
            raise RuntimeError("Provider request timed out") from None

        if self.api_family == "responses":
            return self._extract_responses_text(payload)
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Provider response did not contain a chat message") from None
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            result = "".join(part for part in text_parts if isinstance(part, str)).strip()
            if result:
                return result
        raise RuntimeError("Provider returned an empty or unsupported chat message")

    @staticmethod
    def _extract_responses_text(payload: Any) -> str:
        if isinstance(payload, dict):
            direct_text = payload.get("output_text")
            if isinstance(direct_text, str) and direct_text.strip():
                return direct_text.strip()
            output = payload.get("output", [])
            if isinstance(output, list):
                text_parts = [
                    part["text"]
                    for item in output
                    if isinstance(item, dict) and isinstance(item.get("content"), list)
                    for part in item["content"]
                    if isinstance(part, dict)
                    and part.get("type") == "output_text"
                    and isinstance(part.get("text"), str)
                ]
                result = "".join(text_parts).strip()
                if result:
                    return result
        raise RuntimeError("Provider response did not contain Responses API output text")

    def list_models(self) -> list[str]:
        """Fetch model IDs from the OpenAI-compatible GET /models endpoint."""
        if not self.base_url.startswith(("https://", "http://")):
            raise ValueError("Provider URL must start with http:// or https://")
        endpoint = self.models_url or (
            self.base_url
            if self.base_url.endswith("/models")
            else f"{self.base_url}/models"
        )
        headers = {"Accept": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(endpoint, headers=headers, method="GET")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload: Any = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(_format_http_error(exc)) from None
        except URLError as exc:
            raise RuntimeError(f"Could not reach provider: {exc.reason}") from None
        except TimeoutError:
            raise RuntimeError("Provider request timed out") from None

        try:
            records = payload["data"]
        except (KeyError, TypeError):
            raise RuntimeError("Provider response did not contain a model list") from None
        if not isinstance(records, list):
            raise RuntimeError("Provider response did not contain a model list")
        model_ids = {
            record["id"].strip()
            for record in records
            if isinstance(record, dict)
            and isinstance(record.get("id"), str)
            and record["id"].strip()
        }
        return sorted(model_ids, key=str.casefold)


def build_system_prompt(snapshot: dict[str, str] | None = None) -> str:
    prompt = (
        "You are Bloodborne Copilot. Reply in Brazilian Portuguese, concise and useful, "
        "with spoiler-light advice unless the user asks for spoilers. The user is playing "
        "a Windows port of Bloodborne. Never claim to observe the live game: any save data "
        "below is a persistent snapshot and may be stale. Do not infer the current area, "
        "boss, equipped weapon, quest choice, or real-time HP from that snapshot. Ask a "
        "short clarifying question when needed. Distinguish known snapshot fields from "
        "general game knowledge. Do not suggest editing save files."
    )
    if snapshot:
        safe_fields = {
            key: snapshot[key]
            for key in ("character", "stats", "health", "stamina", "resources", "boss_flags", "inventory")
            if key in snapshot
        }
        prompt += "\n\nLoaded save snapshot (not live telemetry):\n" + json.dumps(
            safe_fields, ensure_ascii=False
        )
    return prompt
