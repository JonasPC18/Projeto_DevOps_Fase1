"""Demonstracao real de deploy, persistencia, rollback, metricas e alerta."""
import base64
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "devops-fase2-demo"
API = "http://127.0.0.1:8000"
PROM = "http://127.0.0.1:9090"
GRAFANA = "http://127.0.0.1:3000"
REPORTS = ROOT / "reports"
events = []


def record(name, **data):
    event = {"step": name, "elapsed_seconds": round(time.monotonic() - started, 2), **data}
    events.append(event)
    print(json.dumps(event, ensure_ascii=False), flush=True)
    (REPORTS / "demonstracao.json").write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n")


def request(url, method="GET", payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", **(headers or {})}
    with urlopen(Request(url, data=data, headers=headers, method=method), timeout=5) as response:
        body = response.read()
        return json.loads(body) if body else None


def wait_for(check, timeout=90):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (OSError, ValueError, KeyError) as error:
            last = type(error).__name__
        time.sleep(2)
    raise RuntimeError(f"Verificacao nao convergiu em {timeout}s; ultimo erro: {last}")


def run(*args, env=None, check=True):
    return subprocess.run(args, cwd=ROOT, env=env, check=check)


def compose(*args):
    return run("docker", "compose", "-p", PROJECT, "-f", "compose.yaml", *args)


def alerts():
    return request(PROM + "/api/v1/alerts")["data"]["alerts"]


if __name__ == "__main__":
    started = time.monotonic()
    REPORTS.mkdir(exist_ok=True)
    image = sys.argv[1]
    if "@sha256:" not in image:
        raise SystemExit("A demonstracao exige uma imagem identificada por digest")
    os.chdir(ROOT)
    os.environ["APP_IMAGE"] = image
    os.environ["COMPOSE_PROJECT_NAME"] = PROJECT
    run("bash", "scripts/deploy.sh", image, PROJECT)
    version = request(API + "/version")["version"]
    if os.environ.get("GITHUB_SHA") and version != os.environ["GITHUB_SHA"]:
        raise RuntimeError("A versao implantada nao corresponde ao commit do workflow")
    record("deploy_aprovado", image=image, version=version)

    task = request(API + "/tasks", "POST", {"title": "Persistencia da demonstracao " + uuid.uuid4().hex[:8]})
    task_url = API + f'/tasks/{task["id"]}'
    compose("restart", "api")
    wait_for(lambda: request(API + "/health")["status"] == "ok")
    assert request(task_url) == task, "Tarefa perdida apos reinicio"
    record("persistencia_apos_reinicio_aprovada")

    broken = "devops-fase2-broken:demo"
    run("docker", "build", "--build-arg", "BASE_IMAGE=" + image, "-t", broken,
        "-f", "tests/Dockerfile.broken", ".")
    env = {**os.environ, "DEPLOY_SKIP_PULL": "1", "DEPLOY_WAIT_TIMEOUT": "25"}
    result = run("bash", "scripts/deploy.sh", broken, PROJECT, env=env, check=False)
    if result.returncode != 1:
        raise RuntimeError(f"A entrega defeituosa deveria retornar 1, recebeu {result.returncode}")
    assert (ROOT / ".deploy" / PROJECT / "current-image").read_text().strip() == image
    assert request(API + "/version")["version"] == version
    assert request(task_url) == task, "Tarefa perdida apos rollback"
    record("rollback_automatico_aprovado", failed_release_rejected=True, data_preserved=True)
    request(task_url, "DELETE")

    query = urlencode({"query": 'up{job="tarefas"}'})
    def target_is_up():
        result = request(PROM + "/api/v1/query?" + query)["data"]["result"]
        return result and result[0]["value"][1] == "1"
    wait_for(target_is_up)
    secret = (ROOT / ".secrets/grafana_admin_password").read_text().strip()
    auth = base64.b64encode(("admin:" + secret).encode()).decode()
    dashboard = wait_for(lambda: request(GRAFANA + "/api/dashboards/uid/devops-tarefas",
                                        headers={"Authorization": "Basic " + auth}))
    assert dashboard["dashboard"]["uid"] == "devops-tarefas"
    (REPORTS / "prometheus-targets.json").write_text(json.dumps(request(PROM + "/api/v1/targets"), indent=2))
    (REPORTS / "grafana-dashboard.json").write_text(json.dumps(dashboard["dashboard"], indent=2))
    record("monitoramento_aprovado", prometheus_up=1, dashboard="devops-tarefas")

    try:
        compose("stop", "api")
        firing = wait_for(lambda: [a for a in alerts() if a["labels"].get("alertname") == "ApiIndisponivel"
                                  and a["state"] == "firing"], timeout=75)
        (REPORTS / "alerta-disparado.json").write_text(json.dumps(firing, indent=2))
        record("alerta_de_indisponibilidade_disparado", state="firing")
    finally:
        compose("start", "api")
        wait_for(lambda: request(API + "/health")["status"] == "ok")
    wait_for(target_is_up)
    wait_for(lambda: not any(a["labels"].get("alertname") == "ApiIndisponivel" for a in alerts()), timeout=60)
    record("alerta_resolvido_e_api_recuperada")
    run("python3", "scripts/smoke_test.py", API)
    logs = subprocess.check_output(["docker", "compose", "-p", PROJECT, "-f", "compose.yaml",
                                    "logs", "--no-color", "--no-log-prefix", "api"], text=True)
    log_events = [json.loads(line) for line in logs.splitlines() if line.strip()]
    assert any(e.get("event") == "http_request" for e in log_events), "Log HTTP JSON ausente"
    (REPORTS / "api-events.json").write_text(json.dumps(log_events, indent=2))
    record("demonstracao_concluida", json_log_events=len(log_events))
