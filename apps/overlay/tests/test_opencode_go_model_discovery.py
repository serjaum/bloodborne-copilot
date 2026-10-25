import json
import queue
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from apps.overlay.chat_client import ProviderSettings
from apps.overlay.overlay import CopilotOverlay


class OpenCodeGoModelDiscoveryTests(unittest.TestCase):
    def test_model_discovery_uses_current_endpoint_and_session_headers(self):
        class Handler(BaseHTTPRequestHandler):
            request_path = None
            authorization = None
            session_id = None
            user_agent = None

            def do_GET(self):
                type(self).request_path = self.path
                type(self).authorization = self.headers.get("Authorization")
                type(self).session_id = self.headers.get("X-OpenCode-Session")
                type(self).user_agent = self.headers.get("User-Agent")
                body = json.dumps({
                    "data": [
                        {"id": "gpt-6-luna"},
                        {"id": "glm-5.3"},
                        {"id": "muse-spark-1.3-contributor"},
                    ],
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
        base_url = f"http://127.0.0.1:{server.server_port}/zen/go/v1"
        models_url = f"{base_url}/models"
        app = object.__new__(CopilotOverlay)
        app.model_result_queue = queue.Queue()
        app.conversation_id = "local-test-conversation"

        app._request_model_list(base_url, "local-test-key", models_url, "opencode_go")

        models, error = app.model_result_queue.get_nowait()
        self.assertIsNone(error)
        self.assertEqual(models, [
            "space-bunny-free",
            "longcat-2.5-preview-free",
            "muse-spark-1.3-contributor",
            "glm-5.3",
            "gpt-6-luna",
        ])
        self.assertEqual(Handler.request_path, "/zen/go/v1/models")
        self.assertEqual(Handler.authorization, "Bearer local-test-key")
        self.assertEqual(Handler.session_id, "local-test-conversation")
        self.assertEqual(Handler.user_agent, "BloodborneCopilot/0.1")

    def test_muse_uses_responses_endpoint_with_session_affinity(self):
        class Handler(BaseHTTPRequestHandler):
            request_path = None
            session_id = None
            user_agent = None
            payload = None

            def do_POST(self):
                type(self).request_path = self.path
                type(self).session_id = self.headers.get("X-OpenCode-Session")
                type(self).user_agent = self.headers.get("User-Agent")
                size = int(self.headers.get("Content-Length", "0"))
                type(self).payload = json.loads(self.rfile.read(size))
                body = json.dumps({"output_text": "Muse mock response"}).encode()
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
        app = object.__new__(CopilotOverlay)
        app.result_queue = queue.Queue()
        app.conversation_id = "muse-test-conversation"
        settings = ProviderSettings(
            base_url=f"http://127.0.0.1:{server.server_port}/zen/go/v1",
            model="muse-spark-1.3-contributor",
            api_key="local-test-key",
            provider="opencode_go",
        )

        app._request_reply([{"role": "user", "content": "Give a short hint."}], settings)

        reply, error = app.result_queue.get_nowait()
        self.assertIsNone(error)
        self.assertEqual(reply, "Muse mock response")
        self.assertEqual(Handler.request_path, "/zen/go/v1/responses")
        self.assertEqual(Handler.session_id, "muse-test-conversation")
        self.assertEqual(Handler.user_agent, "BloodborneCopilot/0.1")
        payload = Handler.payload or {}
        self.assertEqual(payload.get("model"), "muse-spark-1.3-contributor")


if __name__ == "__main__":
    unittest.main()
