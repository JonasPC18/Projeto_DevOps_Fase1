"""API de tarefas para o laboratório de DevOps. Apenas biblioteca padrão."""

import json
import os
import re
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class TaskStore:
    def __init__(self, database):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS tasks ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
                "done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)))"
            )

    def connect(self):
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def as_task(row):
        if row is None:
            raise KeyError("Tarefa não encontrada")
        return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

    def healthy(self):
        with closing(self.connect()) as connection:
            connection.execute("SELECT id FROM tasks LIMIT 1").fetchone()
        return True

    def list_tasks(self):
        with closing(self.connect()) as connection:
            return [self.as_task(row) for row in connection.execute("SELECT * FROM tasks ORDER BY id")]

    def get_task(self, task_id):
        with closing(self.connect()) as connection:
            return self.as_task(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

    def create_task(self, title):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError("O título deve ter entre 1 e 120 caracteres")
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute("INSERT INTO tasks (title) VALUES (?)", (title.strip(),))
            task_id = cursor.lastrowid
        return self.get_task(task_id)

    def update_task(self, task_id, done):
        if type(done) is not bool:
            raise ValueError("O campo done deve ser true ou false")
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(done), task_id))
            if cursor.rowcount == 0:
                raise KeyError("Tarefa não encontrada")
        return self.get_task(task_id)

    def delete_task(self, task_id):
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                raise KeyError("Tarefa não encontrada")


class Metrics:
    """Contadores e histograma com rótulos limitados às rotas conhecidas."""

    buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

    def __init__(self):
        self.lock = threading.Lock()
        self.requests = defaultdict(int)
        self.bucket_counts = [0] * len(self.buckets)
        self.duration_sum = 0.0
        self.duration_count = 0

    @staticmethod
    def route(path):
        path = urlsplit(path).path
        if path in ("/health", "/version", "/tasks", "/metrics"):
            return path
        return "/tasks/{id}" if re.fullmatch(r"/tasks/[1-9][0-9]{0,9}", path) else "other"

    def observe(self, method, route, status, duration):
        with self.lock:
            self.requests[(method, route, status)] += 1
            self.duration_sum += duration
            self.duration_count += 1
            for index, bound in enumerate(self.buckets):
                self.bucket_counts[index] += int(duration <= bound)

    def render(self):
        with self.lock:
            lines = ["# HELP devops_http_requests_total Requisicoes HTTP por metodo, rota e status.",
                     "# TYPE devops_http_requests_total counter"]
            for (method, route, status), count in sorted(self.requests.items()):
                labels = f'method={json.dumps(method)},route={json.dumps(route)},status="{status}"'
                lines.append(f"devops_http_requests_total{{{labels}}} {count}")
            lines += ["# HELP devops_http_request_duration_seconds Duracao das requisicoes HTTP.",
                      "# TYPE devops_http_request_duration_seconds histogram"]
            for bound, count in zip(self.buckets, self.bucket_counts):
                lines.append(f'devops_http_request_duration_seconds_bucket{{le="{bound:g}"}} {count}')
            lines += [f'devops_http_request_duration_seconds_bucket{{le="+Inf"}} {self.duration_count}',
                      f"devops_http_request_duration_seconds_sum {self.duration_sum:.9f}",
                      f"devops_http_request_duration_seconds_count {self.duration_count}"]
        return "\n".join(lines) + "\n"


def handler_for(store, metrics=None):
    metrics = metrics or Metrics()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_args):
            # O evento JSON abaixo substitui o log HTTP padrão.
            pass

        def send_response(self, code, message=None):
            self.response_status = code
            super().send_response(code, message)

        def send_json(self, status, payload=None):
            body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def read_json(self):
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Envie Content-Type: application/json")
            if self.headers.get("Transfer-Encoding") is not None:
                raise ValueError("Transfer-Encoding não é aceito neste laboratório")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError("Envie um JSON de até 4096 bytes")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("O corpo deve ser um objeto JSON")
            return data

        def handle_request(self):
            started = time.monotonic()
            self.response_status = 500
            route = metrics.route(self.path)
            try:
                return self.dispatch()
            finally:
                duration = time.monotonic() - started
                if route != "/metrics":
                    metrics.observe(self.command, route, self.response_status, duration)
                    print(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                                      "event": "http_request", "method": self.command,
                                      "route": route, "status": self.response_status,
                                      "duration_ms": round(duration * 1000, 3)}, ensure_ascii=False),
                          file=sys.stderr, flush=True)

        def dispatch(self):
            path = urlsplit(self.path).path
            match = re.fullmatch(r"/tasks/([1-9][0-9]{0,9})", path)
            task_id = int(match[1]) if match else None
            try:
                if path == "/metrics" and self.command == "GET":
                    body = metrics.render().encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if path == "/version" and self.command == "GET":
                    return self.send_json(200, {"version": os.environ.get("APP_VERSION", "local")})
                if path == "/health" and self.command == "GET":
                    store.healthy()
                    return self.send_json(200, {"status": "ok"})
                if path == "/tasks":
                    if self.command == "GET":
                        return self.send_json(200, store.list_tasks())
                    if self.command == "POST":
                        return self.send_json(201, store.create_task(self.read_json().get("title")))
                    return self.send_json(405, {"error": "Método não permitido"})
                if task_id is not None:
                    if self.command == "GET":
                        return self.send_json(200, store.get_task(task_id))
                    if self.command == "PATCH":
                        return self.send_json(200, store.update_task(task_id, self.read_json().get("done")))
                    if self.command == "DELETE":
                        store.delete_task(task_id)
                        return self.send_json(204)
                    return self.send_json(405, {"error": "Método não permitido"})
                return self.send_json(404, {"error": "Rota não encontrada"})
            except (ValueError, UnicodeDecodeError) as error:
                return self.send_json(400, {"error": str(error)})
            except KeyError:
                return self.send_json(404, {"error": "Tarefa não encontrada"})
            except sqlite3.Error:
                return self.send_json(503, {"error": "Banco de dados indisponível"})

        do_GET = handle_request
        do_POST = handle_request
        do_PATCH = handle_request
        do_DELETE = handle_request
        do_PUT = handle_request

    return Handler


def make_server(host="127.0.0.1", port=8000, database="data/tasks.db"):
    return ThreadingHTTPServer((host, port), handler_for(TaskStore(database)))


if __name__ == "__main__":
    server = make_server(
        os.environ.get("HOST", "127.0.0.1"),
        int(os.environ.get("PORT", "8000")),
        os.environ.get("DB_PATH", "data/tasks.db"),
    )
    print(json.dumps({"event": "startup", "host": server.server_address[0],
                      "port": server.server_address[1], "version": os.environ.get("APP_VERSION", "local")}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
