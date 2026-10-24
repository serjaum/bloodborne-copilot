"""Read-only, experimental Bloodborne save summary reader.

Offsets are based on the community ImHex pattern linked in the README. This is
not an official format or a writer/editor; unknown layouts are rejected.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

INVENTORY_SIGNATURE = bytes.fromhex("40 f0 ff ff")
STAT_OFFSETS = {
    "vitality": 103,
    "endurance": 95,
    "strength": 79,
    "skill": 71,
    "bloodtinge": 63,
    "arcane": 55,
}


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("Save is too short for the detected Bloodborne layout")
    return struct.unpack_from("<I", data, offset)[0]


def _candidate(data: bytes, inventory_offset: int) -> dict[str, Any]:
    username_offset = inventory_offset - 469
    if username_offset < 147 or username_offset + 68832 > len(data):
        raise ValueError("Save is too short for the detected Bloodborne layout")

    raw_name = data[username_offset + 1: inventory_offset]
    raw_name = raw_name[:len(raw_name) - (len(raw_name) % 2)]
    name = raw_name.decode("utf-16le", errors="replace").split("\0", 1)[0].strip()

    stats = {
        name: _u32(data, username_offset - distance)
        for name, distance in STAT_OFFSETS.items()
    }
    level = _u32(data, username_offset - 23)
    if not name or not 1 <= level <= 544 or any(not 1 <= value <= 99 for value in stats.values()):
        raise ValueError("Save signature found, but the character fields failed sanity checks")

    health_current = _u32(data, username_offset - 147)
    health_max = _u32(data, username_offset - 139)
    stamina_current = _u32(data, username_offset - 119)
    stamina_max = _u32(data, username_offset - 111)

    return {
        "character_name": name,
        "level": level,
        "stats": stats,
        "blood_echoes": _u32(data, username_offset - 19),
        "insight": _u32(data, username_offset - 35),
        "health": {"current": health_current, "max": health_max},
        "stamina": {"current": stamina_current, "max": stamina_max},
        "loaded_map_raw": _u32(data, 4),
        "playtime_raw": _u32(data, 8),
        "inventory_signature_offset": inventory_offset,
    }


def parse_save_bytes(data: bytes) -> dict[str, Any]:
    """Parse a conservative summary from a Bloodborne userdata file.

    The reader uses the first community-documented inventory marker, then checks
    every matching marker yields the same character summary before accepting it.
    """
    if len(data) < 1024:
        raise ValueError("File is too small to be a Bloodborne userdata save")
    offsets: list[int] = []
    start = 0
    while True:
        offset = data.find(INVENTORY_SIGNATURE, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + 1
    if not offsets:
        raise ValueError("Bloodborne inventory signature was not found")

    valid: list[dict[str, Any]] = []
    failures: list[str] = []
    for offset in offsets:
        try:
            valid.append(_candidate(data, offset))
        except ValueError as exc:
            failures.append(str(exc))
    if not valid:
        raise ValueError(failures[0] if failures else "No valid Bloodborne character record found")

    comparable_keys = (
        "character_name", "level", "stats", "blood_echoes", "insight", "health", "stamina"
    )
    first = valid[0]
    if any(any(record[key] != first[key] for key in comparable_keys) for record in valid[1:]):
        raise ValueError("Multiple conflicting character records found; refusing an ambiguous parse")

    return {
        "format": "Bloodborne userdata (community layout; experimental)",
        "read_only": True,
        "file_size": len(data),
        "inventory_markers_found": len(offsets),
        **first,
        "field_notes": {
            "loaded_map_raw": "Raw value only; map-name mapping is not yet implemented.",
            "playtime_raw": "Raw value only; units are not yet validated.",
        },
    }


def inspect_save(path: str | Path) -> dict[str, Any]:
    return parse_save_bytes(Path(path).read_bytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a Bloodborne save summary (never modifies the save).")
    parser.add_argument("save", type=Path, help="Path to userdata000X")
    args = parser.parse_args(argv)
    try:
        result = inspect_save(args.save)
    except (OSError, ValueError) as exc:
        print(f"save-reader: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
