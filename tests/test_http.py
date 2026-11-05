import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from app import make_server


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = make_server(port=0, database=Path(self.temp.name) / "tasks.db")
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None, raw=None, content_type="application/json"):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        connection.request(method, path, body=body, headers={"Content-Type": content_type})
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, json.loads(data) if data else None

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))

    def test_complete_task_lifecycle(self):
        status, task = self.request("POST", "/tasks", {"title": "Entregar fase 1"})
        self.assertEqual(status, 201)
        self.assertFalse(task["done"])
        path = f'/tasks/{task["id"]}'
        self.assertEqual(self.request("GET", "/tasks"), (200, [task]))
        self.assertEqual(self.request("GET", path), (200, task))
        status, updated = self.request("PATCH", path, {"done": True})
        self.assertEqual(status, 200)
        self.assertTrue(updated["done"])
        self.assertEqual(self.request("DELETE", path), (204, None))
        self.assertEqual(self.request("GET", path)[0], 404)

    def test_empty_title_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", {"title": " "})[0], 400)

    def test_long_title_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", {"title": "x" * 121})[0], 400)

    def test_missing_title_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", {})[0], 400)

    def test_invalid_json_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", raw=b"{broken")[0], 400)

    def test_json_array_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", payload=[])[0], 400)

    def test_wrong_content_type_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", payload={"title": "Teste"}, content_type="text/plain")[0], 400)

    def test_oversized_body_returns_400(self):
        self.assertEqual(self.request("POST", "/tasks", raw=b" " * 4097)[0], 400)

    def test_invalid_done_returns_400(self):
        _, task = self.request("POST", "/tasks", {"title": "Teste"})
        self.assertEqual(self.request("PATCH", f'/tasks/{task["id"]}', {"done": "true"})[0], 400)

    def test_unknown_task_returns_404(self):
        self.assertEqual(self.request("PATCH", "/tasks/999", {"done": True})[0], 404)

    def test_unknown_route_returns_404(self):
        self.assertEqual(self.request("GET", "/inexistente")[0], 404)

    def test_disallowed_method_returns_405(self):
        self.assertEqual(self.request("PUT", "/tasks", {"title": "Teste"})[0], 405)

    def test_unicode_round_trip(self):
        _, task = self.request("POST", "/tasks", {"title": "Revisar integração contínua"})
        self.assertEqual(self.request("GET", f'/tasks/{task["id"]}')[1]["title"], "Revisar integração contínua")
