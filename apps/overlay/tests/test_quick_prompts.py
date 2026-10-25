import unittest

from apps.overlay.chat_client import QUICK_PROMPTS


class QuickPromptTests(unittest.TestCase):
    def test_compact_actions_cover_build_boss_and_next_step_without_live_claims(self):
        self.assertEqual(set(QUICK_PROMPTS), {"Build", "Boss", "Next step"})
        self.assertIn("weapon", QUICK_PROMPTS["Build"].lower())
        self.assertIn("which boss", QUICK_PROMPTS["Boss"].lower())
        self.assertIn("current area", QUICK_PROMPTS["Next step"].lower())
        self.assertIn("ask", QUICK_PROMPTS["Next step"].lower())


if __name__ == "__main__":
    unittest.main()
