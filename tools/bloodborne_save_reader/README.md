# Bloodborne Save Reader

Read-only, experimental parser for Bloodborne `userdata000X` files. No dependencies beyond Python 3.10+.

From the repository root:

```powershell
python -m tools.bloodborne_save_reader.save_reader "C:\path\to\userdata0000"
```

Outputs JSON. It never writes to the save. Layout details come from community reverse engineering and are best-effort; unknown fields are left raw and ambiguous records are rejected.

Run tests from the repository root:

```powershell
python -m unittest discover -s tools/bloodborne_save_reader/tests -v
```

Personal saves belong under `testdata/private/`, which is ignored by Git. Do not commit them.
