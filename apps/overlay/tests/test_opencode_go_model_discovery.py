import json
import queue
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
                    "data": [{"id": "glm-5.3"}, {"id": "gpt-6-luna"}],
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
        self.assertEqual(models, ["glm-5.3"])
        self.assertEqual(Handler.request_path, "/zen/go/v1/models")
        self.assertEqual(Handler.authorization, "Bearer local-test-key")
        self.assertEqual(Handler.session_id, "local-test-conversation")
        self.assertEqual(Handler.user_agent, "BloodborneCopilot/0.1")


if __name__ == "__main__":
    unittest.main()
