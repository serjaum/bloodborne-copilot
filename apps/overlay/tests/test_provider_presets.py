import unittest

from apps.overlay.providers import PROVIDERS, filter_models_for_provider


class ProviderPresetTests(unittest.TestCase):
    def test_openai_and_opencode_go_use_their_documented_api_routes(self):
        self.assertEqual(PROVIDERS["openai"].label, "OpenAI")
        self.assertEqual(PROVIDERS["openai"].base_url, "https://api.openai.com/v1")
        self.assertEqual(PROVIDERS["openai"].models_url, None)
        self.assertEqual(PROVIDERS["opencode_go"].label, "OpenCode Go")
        self.assertEqual(
            PROVIDERS["opencode_go"].base_url,
            "https://opencode.ai/zen/go/v1",
        )
        self.assertEqual(
            PROVIDERS["opencode_go"].models_url,
            "https://opencode.ai/zen/go/v1/models",
        )
        self.assertEqual(PROVIDERS["opencode_go"].default_model, "glm-5.3")
        self.assertIn("glm-5.3", PROVIDERS["opencode_go"].chat_models or ())
        self.assertNotIn("gpt-6-luna", PROVIDERS["opencode_go"].chat_models or ())

    def test_opencode_go_model_list_only_offers_chat_completions_models(self):
        available = ["gpt-6-luna", "glm-5.3", "claude-haiku-5-5", "kimi-k3"]

        self.assertEqual(
            filter_models_for_provider("opencode_go", available),
            ["glm-5.3", "kimi-k3"],
        )
        self.assertEqual(filter_models_for_provider("openai", available), available)

    def test_custom_openai_compatible_provider_remains_available(self):
        self.assertEqual(PROVIDERS["custom"].label, "Custom / OpenAI-compatible")
        self.assertEqual(PROVIDERS["custom"].base_url, "")


if __name__ == "__main__":
    unittest.main()
