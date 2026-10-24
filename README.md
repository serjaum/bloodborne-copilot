# bloodborne-copilot

Read-only, second-screen AI companion for Bloodborne on Windows (bbport).

## Save reader (prototype)

The first tool reads a Bloodborne `userdata000X` file and prints a JSON summary. It does not modify the input file.

```powershell
python -m src.save_reader "C:\path\to\userdata0000"
```

Currently reports the character name, level, attributes, Blood Echoes, Insight, health, stamina, best-effort boss flags, raw death count, and raw world coordinates. The raw map and playtime values are included but are **not yet decoded or validated**. Boss flags were compared with the bbport trophy log for this local save; that is a cross-check, not a formal format guarantee. The layout is community reverse-engineered, not an official format; unsupported or ambiguous saves are rejected rather than edited.

A local test copy, if present, belongs under `testdata/private/`. That path is ignored by Git: never commit or upload personal save data.

## Tests

```powershell
python -m unittest discover -v
```

## Format reference

The initial offsets are based on the community [Bloodborne ImHex pattern](https://github.com/WerWolv/ImHex-Patterns/blob/master/patterns/bloodborne_save.hexpat). Treat all parsed data as best-effort until validated against more save versions.
