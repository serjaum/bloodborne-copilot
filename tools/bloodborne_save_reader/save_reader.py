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
AOB_SIGNATURE = bytes.fromhex("03 00 00 00 05 00 01 00")
LCED_SIGNATURE = b"LCED"
COORDINATE_MARKER = bytes.fromhex("ff ff ff ff 00 00 00 00 00 00 00 00")
INVENTORY_SLOT_SIZE = 16
CARRIED_INVENTORY_SLOT_COUNT = 1983
STORAGE_OFFSET_FROM_INVENTORY = 34268
STORAGE_SLOT_COUNT = 1984
BOSS_FLAGS = {
    "Cleric Beast": (21714, 0x08),
    "Father Gascoigne": (21727, 0x80),
    "Vicar Amelia": (21602, 0x80),
    "Blood-starved Beast": (21477, 0x80),
    "Darkbeast Paarl": (21464, 0x08),
    "Witch of Hemwick": (21352, 0x80),
    "Celestial Emissary": (21839, 0x08),
    "Ebrietas": (21852, 0x80),
    "Martyr Logarius": (21977, 0x80),
    "Mergo's Wet Nurse": (22102, 0x80),
    "Micolash": (22108, 0x3F),
    "Shadows of Yharnam": (22227, 0x80),
    "The One Reborn": (22352, 0x80),
    "Rom": (22602, 0x80),
    "Amygdala": (22727, 0x80),
    "Ludwig": (22852, 0x80),
    "Laurence": (22858, 0x20),
    "Lady Maria": (22977, 0x80),
    "Living Failures": (22983, 0x20),
    "Orphan of Kos": (23102, 0x80),
    "Moon Presence": (21108, 0x20),
    "Gehrman": (21102, 0x80),
}


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("Save is too short for the detected Bloodborne layout")
    return struct.unpack_from("<I", data, offset)[0]


def _find_all(data: bytes, marker: bytes, start: int = 0, end: int | None = None) -> list[int]:
    positions: list[int] = []
    cursor = start
    limit = len(data) if end is None else min(end, len(data))
    while (position := data.find(marker, cursor, limit)) >= 0:
        positions.append(position)
        cursor = position + 1
    return positions


def _community_extras(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"bosses": None, "boss_flags_raw": None, "death_count_raw": None,
                               "position_raw": None}
    aob_hits = _find_all(data, AOB_SIGNATURE)
    if len(aob_hits) == 1 and aob_hits[0] + max(offset for offset, _ in BOSS_FLAGS.values()) < len(data):
        aob = aob_hits[0]
        raw = {name: data[aob + offset] for name, (offset, _) in BOSS_FLAGS.items()}
        result["boss_flags_raw"] = {name: f"0x{value:02x}" for name, value in raw.items()}
        result["bosses"] = {
            name: (value == mask if name == "Micolash" else bool(value & mask))
            for name, value in raw.items()
            for _, mask in (BOSS_FLAGS[name],)
        }
        result["death_count_raw"] = _u32(data, aob + 360)

    lced_hits = _find_all(data, LCED_SIGNATURE)
    if len(lced_hits) == 1:
        start = lced_hits[0]
        coordinate_hits = _find_all(data, COORDINATE_MARKER, start, start + 10000)
        if len(coordinate_hits) == 1 and coordinate_hits[0] + 24 <= len(data):
            x, y, z = struct.unpack_from("<fff", data, coordinate_hits[0] + 12)
            result["position_raw"] = {"x": x, "y": y, "z": z}
    return result


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


def _parse_marked_inventory_slots(data: bytes, start: int, slot_count: int) -> list[dict[str, Any]]:
    end = start + slot_count * INVENTORY_SLOT_SIZE
    if start < 0 or end > len(data):
        raise ValueError("Save is too short for the detected inventory layout")

    entries: list[dict[str, Any]] = []
    for slot_index in range(slot_count):
        offset = start + slot_index * INVENTORY_SLOT_SIZE
        record = data[offset:offset + INVENTORY_SLOT_SIZE]
        if len(record) != INVENTORY_SLOT_SIZE:
            raise ValueError("Truncated inventory slot")

        if record[7] == 0xB0 and record[11] == 0x40:
            kind = "item"
        elif record[11] == 0x10:
            kind = "armor"
        else:
            continue

        item_id = int.from_bytes(record[8:11] + b"\x00", "little")
        if item_id == 0:
            continue

        entries.append({
            "slot_index": slot_index,
            "slot_number_raw": record[0],
            "kind_candidate": kind,
            "item_id_raw": item_id,
            "first_part_raw": _u32(data, offset + 4),
            "second_part_raw": _u32(data, offset + 8),
            "quantity_raw": _u32(data, offset + 12),
            "record_hex": " ".join(f"{byte:02x}" for byte in record),
        })
    return entries


def _parse_inventory(data: bytes, inventory_offset: int) -> dict[str, list[dict[str, Any]]]:
    storage_offset = inventory_offset + STORAGE_OFFSET_FROM_INVENTORY
    return {
        "carried": _parse_marked_inventory_slots(
            data, inventory_offset, CARRIED_INVENTORY_SLOT_COUNT
        ),
        "storage": _parse_marked_inventory_slots(
            data, storage_offset, STORAGE_SLOT_COUNT
        ),
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
        "inventory": _parse_inventory(data, first["inventory_signature_offset"]),
        **_community_extras(data),
        "field_notes": {
            "inventory": "Only community-marked item and armor records are returned. Weapon candidates and unclassified records are omitted; IDs remain raw and names are not resolved.",
            "loaded_map_raw": "Raw value only; map-name mapping is not yet implemented.",
            "playtime_raw": "Raw value only; units are not yet validated.",
            "bosses": "Best-effort interpretation of community-researched flags; verify against in-game trophies.",
            "position_raw": "Raw world coordinates; not mapped to a named area.",
            "death_count_raw": "Community-researched field; not yet cross-checked against the game UI.",
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
