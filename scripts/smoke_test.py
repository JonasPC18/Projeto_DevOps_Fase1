"""Testa a API real. Recebe a URL e remove apenas a tarefa criada pelo teste."""
import json
import sys
import time
import urllib.error
import urllib.request


def request(base, method, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=body, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        raw = response.read()
        return response.status, json.loads(raw) if raw else None


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    for attempt in range(30):
        try:
            check(request(base, "GET", "/health") == (200, {"status": "ok"}), "Healthcheck inválido")
            break
        except (OSError, RuntimeError):
            if attempt == 29:
                raise
            time.sleep(1)
    status, task = request(base, "POST", "/tasks", {"title": "Verificação automática do CI"})
    check(status == 201, "A API não criou a tarefa")
    path = f'/tasks/{task["id"]}'
    try:
        status, tasks = request(base, "GET", "/tasks")
        check(status == 200 and task in tasks, "Tarefa ausente da listagem")
        status, updated = request(base, "PATCH", path, {"done": True})
        check(status == 200 and updated["done"] is True, "A API não concluiu a tarefa")
    finally:
        check(request(base, "DELETE", path)[0] == 204, "Falha ao remover a tarefa de teste")
    try:
        request(base, "GET", path)
    except urllib.error.HTTPError as error:
        check(error.code == 404, "A API retornou um erro inesperado após a exclusão")
    else:
        raise RuntimeError("A tarefa continuou disponível após a exclusão")
    print("Smoke test aprovado: saúde, criação, listagem, conclusão e exclusão.")


if __name__ == "__main__":
    main()
