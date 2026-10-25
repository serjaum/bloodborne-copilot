import unittest

from apps.overlay.overlay import CopilotOverlay


class _FakeRoot:
    def __init__(self):
        self.cancelled = None
        self.destroyed = False

    def after_cancel(self, callback_id):
        self.cancelled = callback_id

    def destroy(self):
        self.destroyed = True


class OverlayLifecycleTests(unittest.TestCase):
    def test_close_cancels_pending_ui_poll_before_destroying_root(self):
        app = object.__new__(CopilotOverlay)
        app.root = _FakeRoot()
        app.running = True
        app.poll_after_id = "pending-poll"

        app.close()

        self.assertFalse(app.running)
        self.assertEqual(app.root.cancelled, "pending-poll")
        self.assertTrue(app.root.destroyed)
        self.assertIsNone(app.poll_after_id)


if __name__ == "__main__":
    unittest.main()
