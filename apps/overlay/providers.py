"""Built-in API provider presets used by the settings dialog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    label: str
    base_url: str
    default_model: str
    models_url: str | None = None
    chat_models: tuple[str, ...] | None = None
    responses_models: tuple[str, ...] | None = None
    requires_api_key: bool = True


OPENCODE_GO_CHAT_MODELS = (
    "glm-5.3-flash", "glm-5.3", "glm-5.2", "kimi-k3", "kimi-k2.7-code", "kimi-k2.6",
    "longcat-2.0", "longcat-2.5-preview-free", "space-bunny-free",
    "deepseek-v4.1-flash", "deepseek-v4-pro", "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp", "mimo-v2.6-flash", "mimo-v2.6-pro", "mimo-v2.5",
    "mimo-v2.5-pro", "hy4-preview", "hy3",
)

OPENCODE_GO_RESPONSES_MODELS = (
    "grok-4.7", "grok-4.6", "gpt-6-luna", "gpt-5.6-luna",
    "muse-spark-1.3-contributor", "muse-spark-1.2-contributor",
)

OPENCODE_GO_FREE_MODELS = (
    "longcat-2.5-preview-free",
    "space-bunny-free",
)

OPENCODE_GO_PREFERRED_ORDER = (
    "space-bunny-free", "longcat-2.5-preview-free",
    "muse-spark-1.3-contributor", "muse-spark-1.2-contributor",
    "glm-5.3-flash", "mimo-v2.6-flash",
)


PROVIDERS = {
    "openai": ProviderPreset(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
    "opencode_go": ProviderPreset(
        id="opencode_go",
        label="OpenCode Go",
        base_url="https://opencode.ai/zen/go/v1",
        default_model="glm-5.3",
        models_url="https://opencode.ai/zen/go/v1/models",
        chat_models=OPENCODE_GO_CHAT_MODELS,
        responses_models=OPENCODE_GO_RESPONSES_MODELS,
    ),
    "custom": ProviderPreset(
        id="custom",
        label="Custom / OpenAI-compatible",
        base_url="",
        default_model="",
        requires_api_key=False,
    ),
}

PROVIDER_LABELS = {provider.label: provider_id for provider_id, provider in PROVIDERS.items()}


def filter_models_for_provider(provider_id: str, model_ids: list[str]) -> list[str]:
    """Keep only models supported by the app's provider API adapters."""
    preset = PROVIDERS.get(provider_id, PROVIDERS["custom"])
    if preset.chat_models is None and preset.responses_models is None:
        return list(model_ids)
    allowed = set(preset.chat_models or ()) | set(preset.responses_models or ())
    available_ids = list(model_ids)
    if provider_id == "opencode_go":
        available_ids.extend(
            model_id for model_id in OPENCODE_GO_FREE_MODELS if model_id not in available_ids
        )
    available = [model_id for model_id in available_ids if model_id in allowed]
    preferred = {
        model_id: index
        for index, model_id in enumerate(OPENCODE_GO_PREFERRED_ORDER)
    }
    return sorted(
        available,
        key=lambda model_id: (
            preferred.get(model_id, len(preferred)),
            model_id.casefold(),
        ),
    )


def api_family_for_model(provider_id: str, model_id: str) -> str | None:
    """Return the provider API family needed by a selectable model ID."""
    if provider_id != "opencode_go":
        return "chat_completions"
    preset = PROVIDERS["opencode_go"]
    if model_id in (preset.chat_models or ()):
        return "chat_completions"
    if model_id in (preset.responses_models or ()):
        return "responses"
    return None
