# bloodborne-copilot

Read-only, second-screen AI companion for Bloodborne on Windows (bbport).

## Save reader (prototype)

The first tool reads a Bloodborne `userdata000X` file and prints a JSON summary. It does not modify the input file.

```powershell
python -m tools.bloodborne_save_reader.save_reader "C:\path\to\userdata0000"
```

Currently reports the character name, level, six attributes, Blood Echoes, Insight, health/stamina, best-effort boss flags, raw death count, raw world coordinates, raw map ID/playtime, and raw item/armor candidates found in carried inventory/storage. Inventory IDs and quantities are not name-resolved; weapon and unclassified records are omitted. See the [tool README](tools/bloodborne_save_reader/README.md) and [save format map](docs/save-format-map.md) for coverage, confidence, and limitations. The layout is community reverse-engineered, not an official format; unsupported or ambiguous saves are rejected rather than edited.

## Desktop overlay (MVP)

A small, draggable, always-on-top Windows panel can display one read-only save snapshot. It is not live telemetry and does not capture the screen or send game inputs. See [apps/overlay/README.md](apps/overlay/README.md).

```powershell
python -m apps.overlay
```

The overlay reads one save snapshot only. Personal test saves belong under ignored `testdata/private/`; never commit or upload them.

## Tests

```powershell
python -m unittest discover -s tools/bloodborne_save_reader/tests -v
python -m unittest discover -s apps/overlay/tests -v
```

## Format reference

The [save format map](docs/save-format-map.md) is the project’s living index of fields, offsets, evidence levels and unknowns. The initial offsets are based on the community [Bloodborne ImHex pattern](https://github.com/WerWolv/ImHex-Patterns/blob/master/patterns/bloodborne_save.hexpat). Treat all parsed data as best-effort until validated against more save versions.
