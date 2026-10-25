import base64
import json
import tempfile
import unittest
from pathlib import Path

from apps.overlay.settings_store import SettingsStore


class _TestProtector:
    def protect(self, cleartext: bytes) -> bytes:
        return b"sealed:" + cleartext[::-1]

    def unprotect(self, ciphertext: bytes) -> bytes:
        return ciphertext.removeprefix(b"sealed:")[::-1]


class SettingsStoreTests(unittest.TestCase):
    def test_persists_settings_with_api_key_protected_from_plaintext(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path=path, protector=_TestProtector())
            settings = {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "test-model",
                "api_key": "test-key-not-a-real-secret",
            }

            store.save(settings)

            raw = path.read_text(encoding="utf-8")
            stored = json.loads(raw)
            self.assertNotIn(settings["api_key"], raw)
            self.assertIn("api_key_protected", stored)
            self.assertEqual(
                base64.b64decode(stored["api_key_protected"]),
                _TestProtector().protect(settings["api_key"].encode()),
            )
            self.assertEqual(store.load(), settings)

    def test_missing_settings_file_returns_empty_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(path=Path(directory) / "missing.json", protector=_TestProtector())

            self.assertEqual(store.load(), {})


if __name__ == "__main__":
    unittest.main()
