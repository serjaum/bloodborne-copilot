import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from apps.overlay.chat_client import OpenAICompatibleClient


class _TestHandler(BaseHTTPRequestHandler):
    request_path = None
    authorization = None
    payload = None

    def do_POST(self):
        type(self).request_path = self.path
        type(self).authorization = self.headers.get("Authorization")
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

    def log_message(self, _format, *_args):
        pass


class OpenAICompatibleClientTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
