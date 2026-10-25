# Bloodborne Copilot Overlay

A dependency-free Windows MVP for a small, draggable, always-on-top companion panel. It is a separate read-only app; it does not inject into Bloodborne, send game inputs, capture the screen, or call an AI service.

## Run

From the repository root, using Python with Tkinter enabled:

```powershell
python -m apps.overlay
```

Optionally load one save snapshot at launch:

```powershell
python -m apps.overlay --save "C:\path\to\userdata0000"
```

Or choose **LOAD SAVE SNAPSHOT** in the panel. Select a `userdata000X` file; the reader opens it once and does not monitor or modify it.

## Controls

- Drag the title text to move the panel.
- **PINNED** toggles always-on-top behavior.
- **×** or `Esc` closes the panel.
- **LOAD SAVE SNAPSHOT** opens a file picker.

## What it shows

Character name and level, six stats, saved HP/stamina, Blood Echoes/Insight, experimental boss-flag count, and raw inventory-candidate counts. Inventory IDs are not translated into names. Boss flags and inventory markers are experimental; treat them as hints, not authoritative progression data.

All displayed save values are a **snapshot**, not live telemetry. Do not load a save while the game may be writing it. The overlay does not yet observe gameplay or produce contextual AI advice.

## Display limitations

The panel is borderless and semi-transparent. It should stay above ordinary windows and borderless-windowed games; exclusive fullscreen can cover it. Interacting with the panel may take keyboard/mouse focus from the game, so loading the save before play or keeping the panel on a second monitor is recommended.
