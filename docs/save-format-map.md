# Bloodborne Save Format Map — Readable Fields Index

> **Status:** Living project map for `bloodborne-copilot`. This index tracks fields that community patterns and parsers indicate may be readable from a `userdata000X` file. **It is not official FromSoftware documentation** and does not claim that every field is decoded or validated.
>
> **Safety:** Analyze copies read-only. Never publish personal saves, edit the original save, or read a file while the game may be writing it.

## 1. Evidence levels

| Level | Meaning |
|---|---|
| **A — observed in this project** | The local reader extracts the field from compatible samples. Where noted, it was also cross-checked against an external artifact. Not a universal format guarantee. |
| **B — community interpretation** | An ImHex pattern or community editor identifies and interprets the field, but this project has not independently implemented or validated it. |
| **C — raw/experimental** | Bytes or values can be located and reported, but their meaning, units, or association are unconfirmed. |
| **D — unmapped** | The save may contain the data, but its structure or meaning is unknown to this project. |

“Field is present,” “value is interpreted,” and “interpretation is validated” are different claims. This index tracks that distinction.

## 2. File and anchors

- The primary target is a character save named `userdata000X`, with no extension, in the format used by the game/port. A PS4 export may wrap save files and metadata in a ZIP; the ZIP itself is not the character-data block.
- A size of **1,310,720 bytes** was observed in examined samples. Do not treat it as a universal requirement.
- The project reader searches for the inventory marker `40 F0 FF FF`. Call its position **I**.
- A community-researched name/character anchor is **U = I − 469**. This relation is used by the ImHex pattern and community parsers.
- A candidate flags anchor **A** is found using `03 00 00 00 05 00 01 00`. A community parser relates it to **U + 68,545**; this project reader searches for the signature directly.
- `LCED` locates a region near candidate coordinates. The coordinate marker is `FF FF FF FF 00 00 00 00 00 00 00 00`.
- If a marker is missing, ambiguous, or yields implausible fields, the reader should reject the file rather than guess.

## 3. Field index

### 3.1 Header and global state

| Field | Candidate location/encoding | Status | Notes |
|---|---|---:|---|
| Loaded map ID | `F + 4`, little-endian `u32`; `F` is the start of the raw file | **C** | Community pattern and prototype expose the raw value. The ID-to-area-name table is not validated or implemented. |
| Playtime | `F + 8`, little-endian `u32` | **C** | Raw value only; units and conversion are not validated. |
| Moon phase | `A + 6,102`, byte | **C** | Described by the community ImHex pattern; encoding/meaning not checked in-game. |
| Global/event flags | Candidate flags block associated with `A` | **D** | Many bytes look like flags. Only a subset associated with boss states is catalogued below. Do not infer quest meaning from unknown bytes. |

### 3.2 Character identity, stats, and resources

Offsets are relative to **U**. Four-byte integers are little-endian unless noted.

| Field | Offset/encoding | Status | Notes |
|---|---|---:|---|
| Character name | `U + 1`, null-terminated UTF-16LE, up to 32 bytes | **A/B** | The local reader decodes the name. Character-set and boundary handling need more tests. |
| Current HP | `U − 147`, `u32` | **A** | Read from persisted save state; not guaranteed to be live telemetry. |
| Maximum-HP bonus | `U − 143`, `u32` | **B** | Present in the community pattern; not exposed by the project reader. |
| Maximum HP | `U − 139`, `u32` | **A** | The prototype reads this as the maximum. Buff/state effects still need validation. |
| Current stamina | `U − 119`, `u32` | **A** | Persisted value, not a per-frame stream. |
| Maximum-stamina bonus | `U − 115`, `u32` | **B** | Present in the community pattern; not exposed by the project reader. |
| Maximum stamina | `U − 111`, `u32` | **A** | The prototype reads this as the maximum. |
| Level | `U − 23`, `u32` | **A** | Reader sanity-check range: 1–544. |
| Vitality | `U − 103`, `u32` | **A** | Base character stat. |
| Endurance | `U − 95`, `u32` | **A** | Base character stat. |
| Strength | `U − 79`, `u32` | **A** | Base character stat. |
| Skill | `U − 71`, `u32` | **A** | Base character stat. |
| Bloodtinge | `U − 63`, `u32` | **A** | Base character stat. |
| Arcane | `U − 55`, `u32` | **A** | Base character stat. |
| Blood Echoes | `U − 19`, `u32` | **A** | Persisted resource value. |
| Insight | `U − 35`, `u32` | **A** | Persisted resource value. |
| Gender | `U + 35`, byte | **B** | Candidate field; code values are not mapped by this project. |
| Voice | `U + 36`, byte | **B** | Candidate field; code values are not mapped. |
| Origin | `U + 39`, byte | **B** | Candidate field; code values are not mapped. |
| NG cycle | `U + 68,831`, byte | **B** | Community-researched field; values/cycle mapping need controlled validation. |
| Appearance | ASCII `FACE` marker at `I + 34,028`; community editor places appearance data after it (`I + 34,032`) with size `0xEB` bytes | **B/C** | The block is locatable, but this project has not decoded its visual parameters. The ImHex pattern and editor describe the start differently; treat its boundary as a candidate. |

### 3.3 Inventory, storage, and equipment

A community editor models inventory entries as **16-byte slots** and classifies items from record fields/IDs. This is an implementation reference, not an independent validation by this project.

| Region/data | Community-researched location/structure | Status | Possible contents |
|---|---|---:|---|
| Carried inventory | Starts at `I`; records have a 16-byte stride | **A/B (partial extraction)** | The reader emits item and armor marker candidates with raw IDs/fields. Weapons and unclassified records are omitted; names are unresolved. |
| Key inventory | `U + 32,201`; candidate region size 2,204 bytes | **B** | Separate key-item area; not yet scanned by the project reader. |
| Storage box | `I + 34,268` (equivalent to `U + 34,737`); 16-byte stride | **A/B (partial extraction)** | The reader emits item and armor marker candidates. A community editor reserves up to 1,984 entries; this is not an official or project-validated limit. |
| Inventory counters | `U + 453` and `U + 34,257` | **C** | Counters used by the community editor to track/delimit inventory; semantics are not independently confirmed. |
| Storage counters | `U + 34,737` and `U + 68,541` | **C** | Community-editor candidates. The first listed counter coincides with the candidate storage start, so do not treat it as an independently confirmed counter. |
| Upgrade/gem/rune region | Candidate start near `F + 84`; community editor parses records of 40 bytes | **B/C** | Community parser classifies Blood Gems and Caryll Runes and reads IDs, types, and properties. Region boundaries are pattern-detected and need validation in this project. |
| Socketed gems | Community editor describes 60-byte equipment blocks: identifier, article ID, durability/auxiliary fields, then five shape+gem-ID pairs | **B** | May associate a weapon/equipment item with socketed gems; not all auxiliary fields are understood. |
| Gem-slot shapes | Community values: closed, radial, triangle, waning, circle, and droplet | **B** | Codes are recorded by the editor; verify against local samples before using in gameplay advice. |
| Weapons | Article ID, category, durability, sockets; editor interprets `second_part` as fortification level and imprint | **B; not yet extracted by this project** | Includes right/left-hand categories. Normal/Uncanny/Lost imprint and +0…+10 upgrade level are community interpretations. |
| Armor | Records classified as Armor by the editor, with IDs/quantities | **A/B (raw candidates)** | The reader extracts marker-matched records but does not resolve armor names. |
| Items and quantities | IDs and quantities in inventory/storage records | **A/B (raw candidates)** | The reader extracts marker-matched entries and raw quantity/value fields; consumable/material/key/chalice names are unresolved. |
| ISZ-glitch-related bytes | `U + 72,082` in a community editor | **C** | Auxiliary field mentioned by the editor; not used by the copilot. |

### 3.4 Progress and bosses

The **A** marker identifies a candidate flags block. The table lists offsets/masks currently used by this project reader and the community pattern. Most boss states are interpreted using the indicated mask; Micolash has a special equality check against `0x3F` in the local reader.

| Boss | Offset relative to A | Community mask/value | Status |
|---|---:|---:|---|
| Cleric Beast | 21,714 | `0x08` | **B; aggregate cross-check only** |
| Father Gascoigne | 21,727 | `0x80` | **B; aggregate cross-check only** |
| Vicar Amelia | 21,602 | `0x80` | **B; aggregate cross-check only** |
| Blood-starved Beast | 21,477 | `0x80` | **B; aggregate cross-check only** |
| Darkbeast Paarl | 21,464 | `0x08` | **B; aggregate cross-check only** |
| Witch of Hemwick | 21,352 | `0x80` | **B; aggregate cross-check only** |
| Shadows of Yharnam | 22,227 | `0x80` | **B; aggregate cross-check only** |
| The One Reborn | 22,352 | `0x80` | **B; aggregate cross-check only** |
| Rom | 22,602 | `0x80` | **B; aggregate cross-check only** |
| Amygdala | 22,727 | `0x80` | **B; aggregate cross-check only** |
| Celestial Emissary | 21,839 | `0x08` | **B; aggregate cross-check only** |
| Ebrietas | 21,852 | `0x80` | **B; aggregate cross-check only** |
| Martyr Logarius | 21,977 | `0x80` | **B; aggregate cross-check only** |
| Micolash | 22,108 | `0x3F` | **B; special comparison; aggregate cross-check only** |
| Mergo's Wet Nurse | 22,102 | `0x80` | **B; aggregate cross-check only** |
| Gehrman | 21,102 | `0x80` | **B; per-boss cross-check coverage not recorded** |
| Moon Presence | 21,108 | `0x20` | **B; per-boss cross-check coverage not recorded** |
| Ludwig | 22,852 | `0x80` | **B; aggregate cross-check only** |
| Laurence | 22,858 | `0x20` | **B; aggregate cross-check only** |
| Living Failures | 22,983 | `0x20` | **B; aggregate cross-check only** |
| Lady Maria | 22,977 | `0x80` | **B; aggregate cross-check only** |
| Orphan of Kos | 23,102 | `0x80` | **B; aggregate cross-check only** |

**Available cross-check:** 20 boss flags associated with trophies matched the local bbport `trophies.log` in one save sample (20/20). This supports those interpretations for that sample; it does not establish universal compatibility across versions, endings, DLC, or NG+ states. The historical aggregate result does not identify which 20 rows were checked, so no individual boss row should be treated as independently validated until that evidence is recorded per boss.

**Unmapped auxiliary flags:** the community pattern mentions extra Ludwig head/arena bytes near `A + 22,788`, `A + 6,060`, and `A + 6,045`. The source comments express uncertainty; do not treat these as definitive states.

| Field | Location | Status | Notes |
|---|---|---:|---|
| Death counter | `A + 360`, little-endian `u32` | **C** | The prototype reports `death_count_raw`; repeated comparison with the in-game UI is still needed. |
| Quests/NPCs/decisions | General flags block | **D** | No complete flag map has been established. Persistent quest state may exist, but do not assign meaning without controlled before/after save comparisons. |
| Trophies | Separate bbport log, not assumed to be part of `userdata000X` | **B** | Useful for cross-checking; do not confuse it with the save or automatically assign it to a character. |

### 3.5 Location, time, and chalices

| Field | Candidate location/encoding | Status | Notes |
|---|---|---:|---|
| Coordinates X/Y/Z | After the 12-byte marker found after `LCED`; three little-endian `float32` values start at `marker + 12` | **C** | The prototype returns raw coordinates. No area/room/orientation/navigation mapping exists yet. |
| Area/map | `F + 4`, `u32` ID | **C** | Raw field; area-name lookup is not implemented. |
| Playtime | `F + 8`, `u32` | **C** | Raw field; units and update behavior are unvalidated. |
| Chalice data | Community pattern places six structures at `I + 88,328` | **C/D** | Proposed fields include depth, layout, server ID, join requirements, special shops/items, gem effects, layers, and curse modifiers. Not decoded or validated by this project. |

## 4. What this project's reader currently implements

Implemented in `tools/bloodborne_save_reader/save_reader.py` (read-only):

- inventory-marker detection and conservative character-record sanity checks;
- character name, level, six stats, Blood Echoes, Insight, current/max HP, and current/max stamina;
- 22 best-effort boss flags;
- raw death counter;
- raw X/Y/Z coordinates;
- raw map ID and playtime;
- item and armor candidates from carried inventory/storage, with slot metadata, raw IDs/record parts, raw quantity/value, and raw bytes; names and weapon records are not resolved;
- explicit field notes for values that are not decoded.

**Not yet implemented in this reader:** weapon records, item-name lookup, key-inventory parsing, upgrades/imprints, gems/runes/sockets, appearance, gender/voice/origin, NG cycle, named areas, playtime units, quest/NPC flags, and chalice data.

## 5. Limits: a save is not real-time telemetry

A save is persistent state/a snapshot, not a combat-event stream. Even values labelled “current HP,” “position,” or “map” may reflect the last persisted state, not a value updated every frame. A save is not a reliable source for continuously tracking:

- player HP/stamina every frame or moment-to-moment combat changes;
- enemy position, HP, animation, intent, or attack;
- dodge/parry windows, hits, damage just dealt, or events not yet persisted;
- a complete history of player inputs.

The live copilot will need screen capture/OCR/vision or a runtime telemetry interface for that data. Save parsing is better suited to profile, inventory, progression, and persistent context. Do not poll a save while the game may be writing it.

## 6. Work needed to complete the map

1. Add read-only carried-inventory and storage output, preserving raw IDs before resolving names.
2. Resolve item names/descriptions using game-resource tables; record each table's source and version.
3. Decode gems/runes, sockets, weapons, fortification/imprints, and armor; compare with the in-game UI.
4. Expose gender/voice/origin, raw appearance, and NG cycle; validate each with controlled saves.
5. Map area IDs, time units, and the six chalice structures without guessing names or units.
6. Map unknown quest/event flags through one-variable-at-a-time experiments: copy before/after, observe the in-game change, compare bytes.
7. Test different layouts/regions/versions. Promote a field from **B/C** to **A** only with reproducible evidence and tests.

## 7. Technical references

1. [Bloodborne save pattern — ImHex Patterns](https://github.com/WerWolv/ImHex-Patterns/blob/master/patterns/bloodborne_save.hexpat) — candidate signatures/offsets, stats, inventory, NG, appearance, map/time, dungeons, coordinates, and flags.
2. [Bloodborne Save Editor — Noxde](https://github.com/Noxde/Bloodborne-save-editor) — independent community parser. Relevant source files: [`save.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/save.rs), [`constants.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/constants.rs), [`offsets.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/offsets.rs), [`inventory.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/inventory.rs), [`article.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/article.rs), [`slots.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/slots.rs), [`upgrades.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/upgrades.rs), [`position.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/position.rs), [`bosses.rs`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/src/data_handling/bosses.rs), and [`bosses.json`](https://github.com/Noxde/Bloodborne-save-editor/blob/main/src-tauri/resources/bosses.json).
3. [bbport: `runtime_savedata.c`](https://github.com/Supermedo/bloodborne_pc/blob/windows/src/runtime_savedata.c) — save loading/writing behavior in the port.
4. [bbport: `bbport_trophies.py`](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_trophies.py) — reference for local trophy/event cross-checks.
5. [Full Storage Glitch — Bloodborne Wiki](https://www.bloodborne-wiki.com/2024/02/full-storage-glitch.html) — community reference cited by parsers for storage capacity/bounds.
6. [Reader implementation](../tools/bloodborne_save_reader/save_reader.py) and [tests](../tools/bloodborne_save_reader/tests/test_save_reader.py) in this project.

> The Noxde editor is a reference, not a safe substitute for this project's read-only parser. Its file-loading path creates a `.bak` copy and the application includes editing features; do not experiment with personal saves in place.

## 8. Offset glossary

- `F`: start of the raw `userdata000X` file.
- `I`: location of the first `40 F0 FF FF` inventory marker.
- `U`: community-researched name/character anchor, tentatively `I − 469`.
- `A`: location of the `03 00 00 00 05 00 01 00` flags signature.
- `u8`/`u32`: 1-/4-byte integer; numeric values are little-endian unless noted.
- `float32`: 4-byte IEEE-754 value; coordinates are read little-endian.
