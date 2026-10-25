# Bloodborne Copilot Desktop App

A dependency-free Windows companion with two views and an OpenAI-compatible text chat. It runs separately from Bloodborne and never injects into the game or sends game inputs.

## Run

From the repository root, using Python with Tkinter enabled:

```powershell
python -m apps.overlay
```

Or start directly in full view:

```powershell
python -m apps.overlay --full
```

Optionally load a `userdata000X` save snapshot at startup:

```powershell
python -m apps.overlay --save "C:\path\to\userdata0000"
```

Or use **LOAD SAVE** in the app. The selected save is opened once, read-only; do not select a file while the game may be writing it.

## Views

- **Compact:** small, frameless, semi-transparent, draggable, and pinned on top by default. It includes a conversation transcript, text entry, **BUILD**, **BOSS**, and **NEXT** quick prompts, plus buttons to open the full view and provider settings.
- **Full:** normal resizable Windows window with a larger chat and a hunter snapshot sidebar. Use the title bar to maximize it, move it to another monitor, or switch to it with Alt+Tab. **COMPACT** returns to the floating view.

The quick prompts are designed for information the app can actually use: build guidance from loaded stats, spoiler-light boss preparation after the user names a boss, and route help after the user supplies their current area and goal. The app does not know the live area or current boss yet.

## AI provider setup

Choose **OpenAI**, **OpenCode Go**, or **Custom / OpenAI-compatible** in Settings; the first two fill their documented API URLs automatically. **LOAD MODELS** fetches the provider's catalog. OpenCode Go models supported by this app are listed with free previews first; documented free models are added even when the catalog omits them. Muse Spark Contributor models use the Responses API, while the preview-free models use Chat Completions. Other Go models using Anthropic Messages are not offered yet. Muse Contributor pricing is discounted, but prompts and completions may be used to train Meta models and availability is region-limited. OpenCode Go is intended for coding-agent traffic; check whether this companion use fits its terms. The app sends its own user agent and a stable `x-opencode-session` on chat and model discovery. The OpenCode Go preset uses `https://opencode.ai/zen/go/v1` and `/models`, matching the current [Go endpoints and requirements](https://opencode.ai/docs/go/).

Alternatively, set these environment variables before launching:

- `COPILOT_PROVIDER` (`openai`, `opencode_go`, or `custom`; a saved provider is used when unset)
- `OPENAI_API_KEY` and `OPENAI_MODEL` (defaults to `gpt-4o-mini`) for OpenAI or custom providers
- `OPENAI_BASE_URL` (defaults to `https://api.openai.com/v1`) when using `custom`
- `OPENCODE_GO_API_KEY` and `OPENCODE_GO_MODEL` (defaults to `glm-5.3`) for OpenCode Go

Environment keys and model names apply only to their matching provider. The built-in OpenAI and OpenCode Go URLs are fixed; `OPENAI_BASE_URL` is editable only for the custom provider.

The API key field is masked. Enter a key for each provider you plan to test and click **SAVE SETTINGS** once; all keys entered in that dialog are stored separately. On Windows, keys are encrypted with DPAPI for the current Windows user in `%LOCALAPPDATA%\BloodborneCopilot\settings.json`, restored per provider on reopen, and never written in plaintext. Chat history is still session-only. The selected provider receives the user's chat and the small parsed summary (if loaded); the save file and raw inventory records are not uploaded. Review the provider's data policy before use. OpenAI endpoint references: [List models](https://developers.openai.com/api/reference/resources/models/methods/list/) and [Create chat completion](https://platform.openai.com/docs/api-reference/chat/create).

## Snapshot and limitations

The sidebar shows character/level, six stats, saved HP/stamina, Blood Echoes/Insight, experimental boss-flag count, and raw item/armor candidate counts. Inventory IDs are not resolved to names; boss flags and marker classifications are not authoritative progression data.

All save values are a persistent **snapshot**, not live telemetry. The app does not capture the game screen, monitor save changes, or provide real-time AI vision. The system prompt explicitly tells the assistant not to infer current area, boss, equipped weapon, or live HP from the save. It favors concise, spoiler-light answers in Brazilian Portuguese.

The compact view is designed to stay above ordinary windows and borderless-windowed games; exclusive fullscreen can cover it. Clicking chat controls may take keyboard/mouse focus from the game. The full view is a regular Alt+Tab window and is not always-on-top.
