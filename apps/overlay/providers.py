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
    requires_api_key: bool = True


OPENCODE_GO_CHAT_MODELS = (
    "glm-5.3-flash", "glm-5.3", "glm-5.2", "kimi-k3", "kimi-k2.7-code", "kimi-k2.6",
    "longcat-2.0", "deepseek-v4.1-flash", "deepseek-v4-pro", "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp", "mimo-v2.6-flash", "mimo-v2.6-pro", "mimo-v2.5",
    "mimo-v2.5-pro", "hy4-preview", "hy3", "space-bunny", "longcat-2.5-preview-free",
    "step-5-preview-free",
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
        base_url="https://opencode.ai/inference/go/openai/v1",
        default_model="glm-5.3",
        models_url="https://opencode.ai/inference/go/v1/models",
        chat_models=OPENCODE_GO_CHAT_MODELS,
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
    """Keep only known chat-capable models where a provider has mixed API families."""
    supported = PROVIDERS.get(provider_id, PROVIDERS["custom"]).chat_models
    if supported is None:
        return list(model_ids)
    allowed = set(supported)
    return [model_id for model_id in model_ids if model_id in allowed]
