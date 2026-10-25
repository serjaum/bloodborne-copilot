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

Open **SET** in compact view or **SETTINGS** in full view. The client uses the OpenAI-compatible `POST /chat/completions` endpoint and supports a configurable base URL, model, and API key. The default base URL is `https://api.openai.com/v1`; the model is editable. Select **LOAD MODELS** after entering the provider URL and key to request its `GET /models` list, then choose an ID or type one manually. Compatible services can use their own base URL and model, including local endpoints, but model-list support is provider-specific. A listed model may not support chat completions.

Alternatively, set these environment variables before launching:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (defaults to `https://api.openai.com/v1`)
- `OPENAI_MODEL` (defaults to `gpt-4o-mini`)

The API key field is masked. On Windows, **SAVE SETTINGS** stores the API key encrypted with DPAPI for the current Windows user in `%LOCALAPPDATA%\BloodborneCopilot\settings.json`; it is restored when the app reopens and is not written in plaintext. Chat history is still session-only. The selected provider receives the user's chat and the small parsed summary (if loaded); the save file and raw inventory records are not uploaded. Review the provider's data policy before use. OpenAI endpoint references: [List models](https://developers.openai.com/api/reference/resources/models/methods/list/) and [Create chat completion](https://platform.openai.com/docs/api-reference/chat/create).

## Snapshot and limitations

The sidebar shows character/level, six stats, saved HP/stamina, Blood Echoes/Insight, experimental boss-flag count, and raw item/armor candidate counts. Inventory IDs are not resolved to names; boss flags and marker classifications are not authoritative progression data.

All save values are a persistent **snapshot**, not live telemetry. The app does not capture the game screen, monitor save changes, or provide real-time AI vision. The system prompt explicitly tells the assistant not to infer current area, boss, equipped weapon, or live HP from the save. It favors concise, spoiler-light answers in Brazilian Portuguese.

The compact view is designed to stay above ordinary windows and borderless-windowed games; exclusive fullscreen can cover it. Clicking chat controls may take keyboard/mouse focus from the game. The full view is a regular Alt+Tab window and is not always-on-top.
