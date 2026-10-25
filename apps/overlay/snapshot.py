"""Display-safe formatting for save-reader data."""

from __future__ import annotations

from typing import Any


STAT_LABELS = (
    ("vitality", "VIT"),
    ("endurance", "END"),
    ("strength", "STR"),
    ("skill", "SKL"),
    ("bloodtinge", "BLT"),
    ("arcane", "ARC"),
)


def _number(value: Any) -> str:
    return f"{value:,}" if isinstance(value, int) else str(value)


def build_snapshot(data: dict[str, Any]) -> dict[str, str]:
    """Convert parser output into concise, explicitly non-live overlay labels."""
    character = str(data.get("character_name") or "Unknown hunter")
    level = data.get("level")
    character_line = f"{character} · Level {_number(level)}" if level is not None else character

    stats = data.get("stats") or {}
    available_stats = [f"{label} {_number(stats[key])}" for key, label in STAT_LABELS if key in stats]
    stats_line = "   ".join(available_stats) if available_stats else "Stats unavailable"

    health = data.get("health") or {}
    health_line = (
        f"{_number(health['current'])} / {_number(health['max'])}"
        if "current" in health and "max" in health else "Not available"
    )
    stamina = data.get("stamina") or {}
    stamina_line = (
        f"{_number(stamina['current'])} / {_number(stamina['max'])}"
        if "current" in stamina and "max" in stamina else "Not available"
    )

    echoes, insight = data.get("blood_echoes"), data.get("insight")
    resources_line = (
        f"{_number(echoes)} / {_number(insight)}"
        if echoes is not None and insight is not None else "Not available"
    )

    bosses = data.get("bosses")
    if isinstance(bosses, dict):
        boss_line = f"{sum(bool(value) for value in bosses.values())} / {len(bosses)} marked · experimental"
    else:
        boss_line = "Not available"

    inventory = data.get("inventory")
    if isinstance(inventory, dict):
        carried = inventory.get("carried")
        storage = inventory.get("storage")
        if isinstance(carried, list) and isinstance(storage, list):
            carried_label = "candidate" if len(carried) == 1 else "candidates"
            storage_label = "candidate" if len(storage) == 1 else "candidates"
            inventory_line = (
                f"{len(carried)} carried {carried_label}   ·   "
                f"{len(storage)} storage {storage_label}"
            )
        else:
            inventory_line = "Not available"
    else:
        inventory_line = "Not available"

    return {
        "character": character_line,
        "stats": stats_line,
        "health": health_line,
        "stamina": stamina_line,
        "resources": resources_line,
        "boss_flags": boss_line,
        "inventory": inventory_line,
        "disclaimer": "SAVE SNAPSHOT · NOT LIVE GAME TELEMETRY",
    }
