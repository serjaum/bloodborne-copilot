import tkinter as tk
import unittest
from tkinter import ttk

from apps.overlay.overlay import (
    COLORS,
    _configure_settings_combobox,
    _style_settings_entry,
)


class SettingsDialogThemeTests(unittest.TestCase):
    def test_settings_inputs_match_the_dark_overlay_palette(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display is unavailable: {exc}")
        root.withdraw()
        try:
            provider_combo = ttk.Combobox(root, values=("OpenAI", "OpenCode Go"))
            model_combo = ttk.Combobox(root, values=("space-bunny-free",))
            _configure_settings_combobox(root, provider_combo)
            _configure_settings_combobox(root, model_combo)
            api_key = tk.Entry(root)
            base_url = tk.Entry(root)
            _style_settings_entry(api_key)
            _style_settings_entry(base_url, read_only=True)

            self.assertEqual(provider_combo.cget("style"), "Copilot.TCombobox")
            self.assertEqual(model_combo.cget("style"), "Copilot.TCombobox")
            self.assertEqual(api_key.cget("background"), COLORS["panel_alt"])
            self.assertEqual(api_key.cget("foreground"), COLORS["text"])
            self.assertEqual(base_url.cget("readonlybackground"), COLORS["panel_alt"])
            style = ttk.Style(root)
            self.assertEqual(
                style.lookup("Copilot.TCombobox", "fieldbackground"),
                COLORS["panel_alt"],
            )
            popdown = model_combo.tk.eval(
                f"ttk::combobox::PopdownWindow {model_combo}"
            )
            list_background = model_combo.tk.call(
                f"{popdown}.f.l", "cget", "-background"
            )
            list_foreground = model_combo.tk.call(
                f"{popdown}.f.l", "cget", "-foreground"
            )
            self.assertEqual(list_background, COLORS["panel_alt"])
            self.assertEqual(list_foreground, COLORS["text"])
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()