#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
image="${1:?Uso: bash scripts/deploy.sh IMAGEM [PROJETO]}"
project="${2:-devops-fase2}"
[[ "$project" =~ ^[a-z0-9][a-z0-9_-]{2,39}$ ]] || { echo 'Nome de projeto invalido' >&2; exit 2; }
[[ "$image" =~ ^[a-zA-Z0-9][a-zA-Z0-9._/:@-]+$ ]] || { echo 'Referencia de imagem invalida' >&2; exit 2; }
mkdir -p ".deploy/$project"
exec 9>".deploy/$project/lock"
flock -n 9 || { echo 'Ja existe um deploy para este projeto' >&2; exit 2; }
python3 scripts/init_secrets.py
state=".deploy/$project/current-image"
previous=''
if [[ -f "$state" ]]; then previous="$(cat "$state")"; fi
export APP_IMAGE="$image"
export COMPOSE_PROJECT_NAME="$project"
compose=(docker compose -p "$project" -f compose.yaml)
"${compose[@]}" config --quiet
if [[ "${DEPLOY_SKIP_PULL:-0}" != 1 ]]; then docker pull "$image"; fi
# Resolve a porta efetiva, incluindo valores de .env, sem executar seu conteudo.
api_port="$("${compose[@]}" config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["api"]["ports"][0]["published"])')"
if "${compose[@]}" up -d --wait --wait-timeout "${DEPLOY_WAIT_TIMEOUT:-90}" && \
   python3 scripts/smoke_test.py "http://127.0.0.1:$api_port"; then
  if [[ -n "$previous" && "$previous" != "$image" ]]; then
    printf '%s\n' "$previous" > ".deploy/$project/previous-image"
  fi
  printf '%s\n' "$image" > "$state.tmp"
  mv "$state.tmp" "$state"
  printf 'Deploy aprovado: %s\n' "$image"
else
  echo 'Deploy reprovado. Conferindo a versao anterior.' >&2
  "${compose[@]}" logs --no-color --tail 30 api >&2 || true
  if [[ -n "$previous" ]]; then
    export APP_IMAGE="$previous"
    if "${compose[@]}" up -d --wait --wait-timeout 90 && \
       python3 scripts/smoke_test.py "http://127.0.0.1:$api_port"; then
      echo 'Rollback automatico aprovado. O volume foi preservado.' >&2
    else
      echo 'Rollback falhou: intervencao necessaria.' >&2
    fi
  else
    "${compose[@]}" stop api || true
    echo 'Primeiro deploy: nenhuma versao anterior disponivel.' >&2
  fi
  exit 1
fi
