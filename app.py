"""API de tarefas para o laboratório de DevOps. Apenas biblioteca padrão."""

import json
import os
import re
import sqlite3
from contextlib import closing
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


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

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
            path = urlsplit(self.path).path
            match = re.fullmatch(r"/tasks/([1-9][0-9]{0,9})", path)
            task_id = int(match[1]) if match else None
            try:
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
    print(f"API disponível em http://{server.server_address[0]}:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
