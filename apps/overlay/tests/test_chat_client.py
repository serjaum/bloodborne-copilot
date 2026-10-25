import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from apps.overlay.chat_client import OpenAICompatibleClient, ProviderSettings


class _TestHandler(BaseHTTPRequestHandler):
    request_path = None
    authorization = None
    payload = None
    opencode_session = None
    user_agent = None

    def do_POST(self):
        type(self).request_path = self.path
        type(self).authorization = self.headers.get("Authorization")
        type(self).opencode_session = self.headers.get("X-OpenCode-Session")
        type(self).user_agent = self.headers.get("User-Agent")
        size = int(self.headers.get("Content-Length", "0"))
        type(self).payload = json.loads(self.rfile.read(size))
        response = json.dumps({
            "choices": [{"message": {"content": "Use the nearest lamp, hunter."}}]
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        type(self).request_path = self.path
        type(self).authorization = self.headers.get("Authorization")
        response = json.dumps({
            "object": "list",
            "data": [
                {"id": "model-z"},
                {"id": "embedding-model"},
                {"id": "model-a"},
            ],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        pass


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_opencode_environment_uses_its_own_key_and_model(self):
        with patch.dict(os.environ, {
            "COPILOT_PROVIDER": "opencode_go",
            "OPENAI_API_KEY": "openai-key-not-for-opencode",
            "OPENCODE_GO_API_KEY": "opencode-go-test-key",
            "OPENCODE_GO_MODEL": "kimi-k3",
        }, clear=True):
            settings = ProviderSettings.from_environment()

        self.assertEqual(settings.provider, "opencode_go")
        self.assertEqual(settings.base_url, "https://opencode.ai/zen/go/v1")
        self.assertEqual(settings.model, "kimi-k3")
        self.assertEqual(settings.api_key, "opencode-go-test-key")

    def test_posts_chat_completion_to_configured_compatible_endpoint(self):
        _TestHandler.request_path = None
        _TestHandler.authorization = None
        _TestHandler.payload = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        client = OpenAICompatibleClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="test-model",
            api_key="test-key-not-a-real-secret",
        )
        messages = [{"role": "user", "content": "How do I prepare for Gascoigne?"}]

        response = client.complete(messages)

        self.assertEqual(response, "Use the nearest lamp, hunter.")
        self.assertEqual(_TestHandler.request_path, "/v1/chat/completions")
        self.assertEqual(_TestHandler.authorization, "Bearer test-key-not-a-real-secret")
        self.assertEqual(_TestHandler.payload["model"], "test-model")
        self.assertEqual(_TestHandler.payload["messages"], messages)

    def test_sends_configured_opencode_session_headers(self):
        _TestHandler.request_path = None
        _TestHandler.opencode_session = None
        _TestHandler.user_agent = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = OpenAICompatibleClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="glm-5.3",
            api_key="local-test-key",
            extra_headers={
                "X-OpenCode-Session": "stable-session-id",
                "User-Agent": "BloodborneCopilot/0.1",
            },
        )

        client.complete([{"role": "user", "content": "Test"}])

        self.assertEqual(_TestHandler.opencode_session, "stable-session-id")
        self.assertEqual(_TestHandler.user_agent, "BloodborneCopilot/0.1")

    def test_posts_to_responses_api_and_extracts_output_text(self):
        class Handler(BaseHTTPRequestHandler):
            request_path = None
            payload = None

            def do_POST(self):
                type(self).request_path = self.path
                size = int(self.headers.get("Content-Length", "0"))
                type(self).payload = json.loads(self.rfile.read(size))
                body = json.dumps({
                    "output": [{
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Muse response"}],
                    }],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = OpenAICompatibleClient(
            base_url=f"http://127.0.0.1:{server.server_port}/zen/go/v1",
            model="muse-spark-1.3-contributor",
            api_key="local-test-key",
            api_family="responses",
        )
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "What should I try?"},
        ]

        self.assertEqual(client.complete(messages), "Muse response")
        self.assertEqual(Handler.request_path, "/zen/go/v1/responses")
        payload = Handler.payload or {}
        self.assertEqual(payload.get("model"), "muse-spark-1.3-contributor")
        self.assertEqual(payload.get("input"), [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "What should I try?"},
        ])

    def test_surfaces_provider_error_message_from_non_openai_error_schema(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.dumps({
                    "type": "NotAuthenticated",
                    "message": "OpenCode Go key is invalid or inactive",
                }).encode()
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = OpenAICompatibleClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="glm-5.3",
            api_key="local-invalid-test-key",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "HTTP 403.*NotAuthenticated.*invalid or inactive",
        ):
            client.complete([{"role": "user", "content": "Test"}])

    def test_lists_model_ids_from_configured_compatible_endpoint(self):
        _TestHandler.request_path = None
        _TestHandler.authorization = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        client = OpenAICompatibleClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="unused-for-listing",
            api_key="test-key-not-a-real-secret",
        )

        models = client.list_models()

        self.assertEqual(models, ["embedding-model", "model-a", "model-z"])
        self.assertEqual(_TestHandler.request_path, "/v1/models")
        self.assertEqual(_TestHandler.authorization, "Bearer test-key-not-a-real-secret")

    def test_uses_provider_specific_model_list_url_when_configured(self):
        _TestHandler.request_path = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        models_url = f"http://127.0.0.1:{server.server_port}/zen/go/v1/models"
        client = OpenAICompatibleClient(
            base_url=f"http://127.0.0.1:{server.server_port}/zen/go/v1",
            model="glm-5.3",
            api_key="local-test-key",
            models_url=models_url,
        )

        client.list_models()

        self.assertEqual(_TestHandler.request_path, "/zen/go/v1/models")


if __name__ == "__main__":
    unittest.main()
