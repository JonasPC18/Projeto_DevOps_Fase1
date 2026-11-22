"""Cria uma senha local aleatoria sem escreve-la nos logs."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
directory = root / ".secrets"
directory.mkdir(mode=0o700, exist_ok=True)
directory.chmod(0o700)
path = directory / "grafana_admin_password"
try:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
except FileExistsError:
    if not path.read_text().strip():
        raise SystemExit("O arquivo de senha do Grafana esta vazio")
else:
    with os.fdopen(descriptor, "w") as file:
        file.write(secrets.token_urlsafe(32) + "\n")
    # O arquivo montado precisa ser legivel pelo UID 472 do Grafana.
    # O diretorio 0700 restringe o acesso de outros usuarios do host.
    path.chmod(0o644)
print("Senha local do Grafana preparada; conteudo omitido.")
