import unittest

from apps.overlay.window_modes import WINDOW_MODES


class WindowModeTests(unittest.TestCase):
    def test_compact_mode_is_a_translucent_always_on_top_panel(self):
        compact = WINDOW_MODES["compact"]
        self.assertTrue(compact.always_on_top)
        self.assertLess(compact.opacity, 1.0)
        self.assertFalse(compact.decorated)
        self.assertFalse(compact.resizable)

    def test_full_mode_is_a_normal_resizable_window_for_alt_tab(self):
        full = WINDOW_MODES["full"]
        self.assertFalse(full.always_on_top)
        self.assertEqual(full.opacity, 1.0)
        self.assertTrue(full.decorated)
        self.assertTrue(full.resizable)
        self.assertGreater(full.width, WINDOW_MODES["compact"].width)
        self.assertGreater(full.height, WINDOW_MODES["compact"].height)


if __name__ == "__main__":
    unittest.main()
