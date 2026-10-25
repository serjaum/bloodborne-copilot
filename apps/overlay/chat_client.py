"""OpenAI-compatible chat completions client and Bloodborne context prompt."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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

    @classmethod
    def from_environment(cls) -> "ProviderSettings":
        return cls(
            base_url=os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip(),
            model=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip(),
            api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        )


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 45.0,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.model = model.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.base_url.startswith(("https://", "http://")):
            raise ValueError("Provider URL must start with http:// or https://")
        if not self.model:
            raise ValueError("Enter a model name in Settings")

        endpoint = (
            self.base_url
            if self.base_url.endswith("/chat/completions")
            else f"{self.base_url}/chat/completions"
        )
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        request = Request(endpoint, data=body, headers=headers, method="POST")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload: Any = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = ""
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                detail = str(error_payload.get("error", {}).get("message", ""))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"Provider returned HTTP {exc.code}{suffix}") from None
        except URLError as exc:
            raise RuntimeError(f"Could not reach provider: {exc.reason}") from None
        except TimeoutError:
            raise RuntimeError("Provider request timed out") from None

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
