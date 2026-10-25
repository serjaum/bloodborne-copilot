import unittest

from apps.overlay.snapshot import build_snapshot


class BuildSnapshotTests(unittest.TestCase):
    def test_builds_a_read_only_hunter_summary_from_reader_output(self):
        reader_output = {
            "character_name": "Hunter",
            "level": 86,
            "stats": {
                "vitality": 30,
                "endurance": 28,
                "strength": 14,
                "skill": 9,
                "bloodtinge": 5,
                "arcane": 50,
            },
            "blood_echoes": 30119,
            "insight": 24,
            "health": {"current": 821, "max": 1100},
            "stamina": {"current": 129, "max": 129},
            "bosses": {"Cleric Beast": True, "Father Gascoigne": False},
            "inventory": {"carried": [{}, {}], "storage": [{}]},
        }

        result = build_snapshot(reader_output)

        self.assertEqual(result["character"], "Hunter · Level 86")
        self.assertEqual(result["stats"], "VIT 30   END 28   STR 14   SKL 9   BLT 5   ARC 50")
        self.assertEqual(result["health"], "821 / 1,100")
        self.assertEqual(result["stamina"], "129 / 129")
        self.assertEqual(result["resources"], "30,119 / 24")
        self.assertEqual(result["boss_flags"], "1 / 2 marked · experimental")
        self.assertEqual(result["inventory"], "2 carried candidates   ·   1 storage candidate")
        self.assertIn("snapshot", result["disclaimer"].lower())

    def test_missing_experimental_sections_render_without_crashing(self):
        result = build_snapshot({
            "character_name": "Test",
            "level": 1,
            "stats": {},
            "health": {},
            "stamina": {},
        })

        self.assertEqual(result["boss_flags"], "Not available")
        self.assertEqual(result["inventory"], "Not available")
        self.assertEqual(result["resources"], "Not available")


if __name__ == "__main__":
    unittest.main()
