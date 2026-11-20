#!/usr/bin/env bash
# Verificación canónica del repo. Falla ruidosamente (set -e); nada se omite en silencio.
#   scripts/check.sh              pruebas locales + stack Docker en http://localhost:8080
#   scripts/check.sh --sin-stack  solo pruebas locales (omisión explícita)
# shortcut: en Windows 20 pruebas dependen de hnswlib (solo Linux) y se saltan; las 30 corren con el comando de Docker de CLAUDE.md.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== [1/2] pytest local"
PYTHONIOENCODING=utf-8 uv run pytest -q

if [[ "${1:-}" == "--sin-stack" ]]; then
  echo "== [2/2] stack OMITIDO (--sin-stack)"; exit 0
fi

echo "== [2/2] stack: /api/health y una búsqueda real"
curl -sf http://localhost:8080/api/health \
  || { echo "ERROR: la API no responde en :8080 · WHY: el stack no está arriba · FIX: docker compose up -d --build"; exit 1; }
echo
curl -sf -X POST http://localhost:8080/api/search -H 'Content-Type: application/json' \
  -d '{"query":"chill acoustic songs for studying","k":3}' \
  | PYTHONIOENCODING=utf-8 uv run python -c "import sys,json; r=json.load(sys.stdin)['results']; assert len(r)>=1, 'búsqueda sin resultados'; print(len(r),'resultados; primero:',r[0]['title'],'-',r[0]['artist'])"
echo "OK"

if [[ "${1:-}" == "--e2e" ]]; then
  echo "== [e2e] Playwright (requiere: cd e2e && npm install && npx playwright install chromium)"
  (cd e2e && npx playwright test)
fi
