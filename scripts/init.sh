#!/usr/bin/env bash
# Arranque canónico: de un clon limpio a http://localhost:8080. Idempotente: salta lo que ya existe.
#   scripts/init.sh              dependencias + datos (bronce, plata, oro) + stack + verificación
#   scripts/init.sh --sin-stack  igual, sin levantar docker compose
# Para rehacer plata u oro: borra data/silver/_manifest.json o data/gold/_manifest.json y vuelve a correrlo.
# Bronce es write-once (si cambia el hash, falla a propósito).
# Windows: ejecutar desde Git Bash o WSL.
set -euo pipefail
cd "$(dirname "$0")/.."

fail() { echo "ERROR: $1 · WHY: $2 · FIX: $3" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "falta '$1'" "$2" "$3"; }

STACK=1
for a in "$@"; do
  case "$a" in
    --sin-stack) STACK=0 ;;
    *) fail "argumento desconocido '$a'" "solo existe --sin-stack" "scripts/init.sh [--sin-stack]" ;;
  esac
done

echo "== [0/5] requisitos"
need uv "gestiona Python 3.14 y las dependencias" "instala uv: https://docs.astral.sh/uv/getting-started/installation/"
need docker "hnswlib solo compila en Linux: el índice se construye y se sirve dentro de Docker" "instala Docker Desktop: https://www.docker.com/products/docker-desktop/"
docker info >/dev/null 2>&1 || fail "el motor de Docker no responde" "las capas oro y el stack corren en contenedores" "abre Docker Desktop, espera a que arranque y reintenta"
export PYTHONIOENCODING=utf-8  # consola de Windows en cp1252

echo "== [1/5] dependencias de Python (uv sync)"
uv sync

echo "== [2/5] bronce y plata (datos de Kaggle)"
if [[ ! -f data/bronze/_manifest.json ]]; then
  if [[ ! -f data/raw/track_data_final.csv ]]; then
    # kagglehub baja el dataset público; si pide credenciales: https://www.kaggle.com/docs/api
    uv run python -c "from src.spotify_eda import Config, download_raw; download_raw(Config())" \
      || fail "no se pudo descargar el dataset de Kaggle" "kagglehub falló (red o credenciales; en una máquina nueva puede pedir KAGGLE_USERNAME/KAGGLE_KEY: POR VERIFICAR)" "define KAGGLE_USERNAME y KAGGLE_KEY, o copia los CSV a data/raw/ y reintenta"
  fi
  uv run python -m src.pipeline bronze
else
  echo "bronce ya existe: se salta"
fi
if [[ ! -f data/silver/_manifest.json ]]; then uv run python -m src.pipeline silver; else echo "plata ya existe: se salta"; fi

echo "== [3/5] oro: embeddings e5-base + índice HNSW (dentro de Docker)"
if [[ ! -f data/gold/_manifest.json ]]; then
  echo "Aviso: primera vez tarda ~15 min en CPU (medido: 16 min en un i7-13700H) y descarga ~1 GB del modelo desde HuggingFace."
  docker build -f docker/api.Dockerfile --target dev -t spotify-dev .
  ROOT_HOST="$(pwd -W 2>/dev/null || pwd)"   # ruta Windows en Git Bash, ruta normal en Linux/macOS
  MSYS_NO_PATHCONV=1 docker run --rm -v "${ROOT_HOST}:/work" \
    -v spotify-global-semantic-search_hf_cache:/root/.cache/huggingface \
    spotify-dev python -m src.pipeline gold
else
  echo "oro ya existe: se salta"
fi

if [[ "$STACK" == 0 ]]; then echo "== stack OMITIDO (--sin-stack)"; exit 0; fi

echo "== [4/5] stack: docker compose up"
docker compose up -d --build
for i in $(seq 1 60); do
  curl -sf http://localhost:8080/api/health >/dev/null 2>&1 && break
  [[ "$i" == 60 ]] && fail "la API no quedó healthy en ~4 min" "el modelo tarda en cargar en CPU o el puerto 8080 está ocupado" "docker compose logs api  (y revisa que nada más use el puerto 8080)"
  sleep 4
done

echo "== [5/5] verificación"
scripts/check.sh
echo "Listo: http://localhost:8080"
