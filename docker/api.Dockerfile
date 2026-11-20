# Contexto de build: la raiz del repo.
#   API (imagen final):  docker compose build api        (o docker build -f docker/api.Dockerfile .)
#   Oro y pruebas:       docker build -f docker/api.Dockerfile --target dev -t spotify-dev .
#                        ver README / informe para los `docker run` exactos.
# Python 3.12 y no 3.14: hnswlib solo publica codigo fuente y se compila en Linux (etapa `wheels`);
# las dependencias fijadas se verificaron como resolubles para cp312 manylinux.

# --- etapa 1: compilar hnswlib (gcc se queda aqui, no llega a la imagen final) ---
FROM python:3.12-slim AS wheels
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*
RUN pip wheel --no-cache-dir hnswlib==0.8.0 -w /wheels

# --- etapa 2: dependencias de ejecucion + codigo ---
FROM python:3.12-slim AS base
WORKDIR /app
# torch solo CPU (la ruta por defecto de PyPI en Linux arrastra CUDA, varios GB)
RUN pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir flask==3.1.3 gunicorn==27.0.1 \
      sentence-transformers==6.3.0 polars==2.1.0 numpy==2.5.5
COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
COPY src src
ENV GOLD_DIR=/app/data/gold \
    HF_HOME=/root/.cache/huggingface

# --- etapa de desarrollo: pytest + git (el manifiesto registra el commit). Se monta el repo en /work ---
FROM base AS dev
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==9.2.0 \
 && git config --global --add safe.directory '*'
WORKDIR /work

# --- imagen final (la ultima etapa es la que construye compose) ---
FROM base
EXPOSE 5000
# 1 worker: el modelo (~1 GB) y el indice viven en memoria una sola vez; hilos para atender en paralelo.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "300", "src.api.app:create_app()"]
