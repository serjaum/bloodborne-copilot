import unittest

from apps.overlay.providers import (
    PROVIDERS,
    api_family_for_model,
    filter_models_for_provider,
)


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

    def test_opencode_go_model_list_only_offers_supported_api_models(self):
        available = ["gpt-6-luna", "glm-5.3", "claude-haiku-5-5", "kimi-k3"]

        self.assertEqual(
            filter_models_for_provider("opencode_go", available),
            [
                "space-bunny-free",
                "longcat-2.5-preview-free",
                "glm-5.3",
                "gpt-6-luna",
                "kimi-k3",
            ],
        )
        self.assertEqual(filter_models_for_provider("openai", available), available)

    def test_opencode_go_model_filter_includes_responses_and_free_chat_models(self):
        available = [
            "gpt-6-luna",
            "glm-5.3",
            "claude-haiku-5-5",
            "muse-spark-1.3-contributor",
            "space-bunny-free",
            "longcat-2.5-preview-free",
        ]

        self.assertEqual(
            filter_models_for_provider("opencode_go", available),
            [
                "space-bunny-free",
                "longcat-2.5-preview-free",
                "muse-spark-1.3-contributor",
                "glm-5.3",
                "gpt-6-luna",
            ],
        )
        self.assertEqual(
            api_family_for_model("opencode_go", "muse-spark-1.3-contributor"),
            "responses",
        )
        self.assertEqual(
            api_family_for_model("opencode_go", "space-bunny-free"),
            "chat_completions",
        )
        self.assertIsNone(api_family_for_model("opencode_go", "claude-haiku-5-5"))
        supplemented = filter_models_for_provider("opencode_go", ["glm-5.3"])
        self.assertIn("longcat-2.5-preview-free", supplemented)
        self.assertIn("space-bunny-free", supplemented)

    def test_custom_openai_compatible_provider_remains_available(self):
        self.assertEqual(PROVIDERS["custom"].label, "Custom / OpenAI-compatible")
        self.assertEqual(PROVIDERS["custom"].base_url, "")


if __name__ == "__main__":
    unittest.main()
