# Bloodborne Save Reader

Read-only, experimental parser for Bloodborne `userdata000X` files. No dependencies beyond Python 3.10+.

From the repository root:

```powershell
python -m tools.bloodborne_save_reader.save_reader "C:\path\to\userdata0000"
```

The reader outputs JSON and never writes to the save. Layout details come from community reverse engineering and are best-effort. It reports only the fields listed below; it does **not** decode the entire file or automatically interpret unknown bytes.

## Fields currently extracted

- **Character:** name, level, Vitality, Endurance, Strength, Skill, Bloodtinge, Arcane.
- **Resources:** Blood Echoes, Insight, current/maximum HP, current/maximum stamina.
- **Progress:** 22 best-effort boss-defeat flags. A previous cross-check matched 20 trophy-associated flags against one local bbport trophy log (20/20); this is not a universal guarantee.
- **Raw/experimental values:** death counter (`death_count_raw`), world coordinates (`position_raw`), loaded map ID (`loaded_map_raw`), and playtime (`playtime_raw`). Coordinates are not mapped to named areas; map IDs and playtime units are not decoded or validated; the death counter has not been checked against the in-game UI.
- **Safety/diagnostics:** reports that parsing is read-only, the file size, detected inventory-marker count, and field notes for unvalidated values.

Inventory/storage contents, item names and quantities, weapons and upgrades, armor, gems/runes, appearance, NG cycle, named locations, chalice data, and quest/NPC flags are **not yet decoded** by this tool. The project-wide [save format map](../../docs/save-format-map.md) records current offsets, evidence levels, references, and open work.

## Run tests

From the repository root:

```powershell
python -m unittest discover -s tools/bloodborne_save_reader/tests -v
```

Personal saves belong under `testdata/private/`, which is ignored by Git. Do not commit them.
