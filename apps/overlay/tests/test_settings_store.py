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
            self.assertIn("api_keys_protected", stored)
            self.assertEqual(
                base64.b64decode(stored["api_keys_protected"]["openai"]),
                _TestProtector().protect(settings["api_key"].encode()),
            )
            self.assertEqual(store.load()["api_key"], settings["api_key"])
            self.assertEqual(store.load()["provider"], settings["provider"])
            self.assertEqual(store.load()["base_url"], settings["base_url"])
            self.assertEqual(store.load()["model"], settings["model"])

    def test_keeps_encrypted_api_keys_separate_for_each_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(
                path=Path(directory) / "settings.json",
                protector=_TestProtector(),
            )
            store.save({
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "api_key": "openai-test-key",
            })
            store.save({
                "provider": "opencode_go",
                "base_url": "https://opencode.ai/inference/go/openai/v1",
                "model": "glm-5.3",
                "api_key": "opencode-test-key",
            })

            loaded = store.load()
            raw = store.path.read_text(encoding="utf-8")

            self.assertEqual(loaded["api_keys"], {
                "openai": "openai-test-key",
                "opencode_go": "opencode-test-key",
            })
            self.assertEqual(loaded["api_key"], "opencode-test-key")
            self.assertNotIn("openai-test-key", raw)
            self.assertNotIn("opencode-test-key", raw)

    def test_saves_multiple_provider_keys_entered_before_one_save(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(
                path=Path(directory) / "settings.json",
                protector=_TestProtector(),
            )

            store.save({
                "provider": "opencode_go",
                "base_url": "https://opencode.ai/inference/go/openai/v1",
                "model": "glm-5.3",
                "api_key": "opencode-go-key",
                "api_keys": {
                    "openai": "openai-key",
                    "opencode_go": "opencode-go-key",
                },
            })

            self.assertEqual(store.load()["api_keys"], {
                "openai": "openai-key",
                "opencode_go": "opencode-go-key",
            })

    def test_missing_settings_file_returns_empty_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(path=Path(directory) / "missing.json", protector=_TestProtector())

            self.assertEqual(store.load(), {})


if __name__ == "__main__":
    unittest.main()
