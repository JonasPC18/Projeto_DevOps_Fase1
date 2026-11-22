import io
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import Metrics, make_server


@contextmanager
def running_api():
    with tempfile.TemporaryDirectory() as directory:
        server = make_server(port=0, database=Path(directory) / "tasks.db")
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class MetricsTests(unittest.TestCase):
    def test_histogram_is_cumulative(self):
        metrics = Metrics()
        metrics.observe("GET", "/tasks", 200, 0.02)
        text = metrics.render()
        self.assertIn('le="0.01"} 0', text)
        self.assertIn('le="0.025"} 1', text)
        self.assertIn('le="+Inf"} 1', text)
        self.assertIn('devops_http_request_duration_seconds_sum 0.020000000', text)

    def test_labels_never_contain_task_ids_or_query(self):
        self.assertEqual(Metrics.route("/tasks/123?token=private"), "/tasks/{id}")
        self.assertEqual(Metrics.route("/private/value"), "other")

    def test_concurrent_updates_are_not_lost(self):
        metrics = Metrics()
        workers = [threading.Thread(target=lambda: [metrics.observe("GET", "/health", 200, 0.01)
                                                    for _ in range(100)]) for _ in range(4)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join()
        self.assertIn('status="200"} 400', metrics.render())
        self.assertEqual(metrics.duration_count, 400)


class ObservabilityHttpTests(unittest.TestCase):
    def test_metrics_endpoint_has_prometheus_content_type(self):
        with running_api() as base:
            with urlopen(base + "/metrics") as response:
                self.assertIn("text/plain", response.headers["Content-Type"])
                self.assertIn(b"# TYPE devops_http_requests_total counter", response.read())

    def test_version_identifies_release(self):
        with patch.dict("os.environ", {"APP_VERSION": "commit-test"}), running_api() as base:
            with urlopen(base + "/version") as response:
                self.assertEqual(json.load(response), {"version": "commit-test"})

    def test_logs_do_not_expose_payload_or_query(self):
        output = io.StringIO()
        with patch("app.sys.stderr", output), running_api() as base:
            request = Request(base + "/tasks?token=private", data=b'{"title":"private-title"}',
                              headers={"Content-Type": "application/json"})
            with urlopen(request) as response:
                response.read()
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[0]["route"], "/tasks")
        self.assertEqual(events[0]["status"], 201)
        self.assertNotIn("private", output.getvalue())

    def test_database_failure_is_counted_as_503(self):
        with running_api() as base:
            with patch("app.TaskStore.healthy", side_effect=sqlite3.OperationalError()):
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/health")
                self.assertEqual(error.exception.code, 503)
            deadline = time.monotonic() + 1
            while True:
                with urlopen(base + "/metrics") as response:
                    text = response.read().decode()
                if 'route="/health",status="503"} 1' in text or time.monotonic() > deadline:
                    break
                time.sleep(0.01)
            self.assertIn('route="/health",status="503"} 1', text)
