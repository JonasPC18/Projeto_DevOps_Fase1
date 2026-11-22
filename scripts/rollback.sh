#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
project="${1:-devops-fase2}"
[[ "$project" =~ ^[a-z0-9][a-z0-9_-]{2,39}$ ]] || exit 2
previous=".deploy/$project/previous-image"
[[ -s "$previous" ]] || { echo 'Nenhuma versao anterior registrada' >&2; exit 1; }
exec bash scripts/deploy.sh "$(cat "$previous")" "$project"
