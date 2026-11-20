# spotify-global-semantic-search

Buscador semántico sobre el [Spotify Global Music Dataset (2009–2025)](https://www.kaggle.com/datasets/wardabilal/spotify-global-music-dataset-20092025):
escribes una frase en lenguaje natural (español o inglés) y obtienes las canciones más similares de un catálogo de 8 778 canciones.

```
Kaggle CSV → bronce (copia inmutable) → plata (tipado + QA) → oro (embeddings e5 + índice HNSW) → API Flask → front React
```

Es un demo de portafolio, no un producto: la calidad de los resultados **no está medida todavía** (ver [Estado](#estado-y-límites)).

## Requisitos

| Qué | Para qué |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (corriendo) | `hnswlib` solo compila en Linux: el índice se construye y se sirve en contenedores |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | gestiona Python 3.14 y las dependencias |
| Git Bash o WSL (en Windows) | los scripts son `bash` |
| Node 20+ | solo para el front en desarrollo y las pruebas E2E |
| Espacio y tiempo | la primera vez baja ~1 GB del modelo y tarda ~15 min en CPU (medido: 16 min en un i7-13700H, 24 GB de RAM, sin GPU). Espacio en disco y RAM mínimos: **POR VERIFICAR** |

## Inicio rápido

```bash
git clone <url-del-repo> && cd spotify-global-semantic-search
scripts/init.sh
```

Al terminar, abre **http://localhost:8080**. `init.sh` es idempotente: salta lo que ya existe, así que puedes repetirlo.

Qué hace, por si prefieres ir paso a paso:

```bash
uv sync                                                    # dependencias de Python
uv run python -c "from src.spotify_eda import Config, download_raw; download_raw(Config())"   # CSV de Kaggle -> data/raw
uv run python -m src.pipeline bronze                       # copia inmutable con SHA-256
uv run python -m src.pipeline silver                       # tablas tipadas + 33 controles de QA
docker build -f docker/api.Dockerfile --target dev -t spotify-dev .
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/work" \
  -v spotify-global-semantic-search_hf_cache:/root/.cache/huggingface \
  spotify-dev python -m src.pipeline gold                  # embeddings + índice HNSW (solo en Docker)
docker compose up -d --build                               # api + web en :8080
```

Para rehacer plata u oro borra `data/silver/_manifest.json` o `data/gold/_manifest.json` y vuelve a correr. **Bronce es write-once**: si el hash de un CSV cambia, falla a propósito.

## Verificar

```bash
scripts/check.sh              # pytest local + /api/health + una búsqueda real contra el stack
scripts/check.sh --sin-stack  # solo las pruebas locales
```

En Windows `pytest` salta 20 de las 30 pruebas (dependen de `hnswlib`). Las 30 corren dentro de Docker:

```bash
docker build -f docker/api.Dockerfile --target dev -t spotify-dev .
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/work" spotify-dev python -m pytest -q -p no:cacheprovider
```

**Pruebas E2E del front (Playwright)**, con el stack arriba:

```bash
cd e2e && npm install && npx playwright install chromium    # una sola vez (baja Chromium)
npx playwright test                                         # o, desde la raíz: scripts/check.sh --e2e
```

`E2E_BASE_URL` cambia la URL a probar (por defecto `http://localhost:8080`).

## Desarrollo del front

```bash
cd web && npm install
node mock-api.mjs      # API simulada con datos falsos, puerto 5000
npm run dev            # http://localhost:5173 (proxy /api -> :5000)
npm test
```

## Cómo está organizado

| Qué | Dónde |
|---|---|
| Qué se construye y criterios de aceptación | [`SPEC.md`](SPEC.md) |
| Por qué se decidió así | [`DECISIONS.md`](DECISIONS.md) |
| Plata: carga, tipado, hallazgos y QA | `src/spotify_eda.py` |
| Pipeline bronce/plata/oro, manifiestos y linaje | `src/pipeline.py`, `data/{bronze,silver,gold,_lineage,_catalog}` |
| Encoder `multilingual-e5-base` | `src/encoder.py` |
| API Flask (`GET /health`, `POST /search`) | `src/api/app.py` |
| Evaluación BM25 vs semántico | `src/eval.py`, `data/gold/eval/golden_queries.json` |
| Front React | `web/` |
| Pruebas E2E | `e2e/` |
| EDA del dataset (notebook y gráficos) | `notebooks/`, `artifacts/` |

Cada capa de datos lleva un `_manifest.json` (entradas y salidas con SHA-256, controles de QA, código y commit) y agrega una línea a `data/_lineage/lineage.jsonl`. Los datos generados no se versionan: se regeneran con `scripts/init.sh`.

## Problemas frecuentes

| Síntoma | Causa | Arreglo |
|---|---|---|
| `el motor de Docker no responde` | Docker Desktop apagado | ábrelo y espera a que arranque |
| `hnswlib` falla al instalar en Windows | no hay compilador de C++ | no hace falta: el índice se construye en Docker |
| `no se pudo descargar el dataset de Kaggle` | red o credenciales | define `KAGGLE_USERNAME` y `KAGGLE_KEY`, o copia los CSV a `data/raw/` (**POR VERIFICAR** si una máquina nueva los pide) |
| La API tarda ~30 s en responder tras arrancar | carga el modelo en CPU | espera al estado `healthy` (`docker compose ps`) |
| El puerto 8080 está ocupado | otro servicio | cambia `8080:80` en `docker-compose.yml` |
| Acentos rotos en la consola de Windows | cp1252 | `PYTHONIOENCODING=utf-8` (los scripts ya lo fijan) |

## Estado y límites

- **Calidad sin medir:** el conjunto dorado (25 consultas) está sin etiquetar, así que `src/eval.py` no se ha ejecutado y no se afirma que el buscador semántico supere a BM25.
- **Datos pobres:** no hay letras ni audio features; solo metadatos. El género falta en el 51 % de las canciones y pertenece al **artista**. Es una muestra del catálogo de Spotify, no el catálogo completo.
- **Sin medir:** latencia por consulta y reproducibilidad del índice entre corridas.
- **Sin CI** configurado.
- **Licencias del dataset de Kaggle y de los modelos: POR VERIFICAR** antes de publicar el demo.

## Trabajar con Claude Code

El contexto para agentes vive en [`.claude/CLAUDE.md`](.claude/CLAUDE.md); el estado del trabajo, en [`feature_list.json`](feature_list.json) y [`PROGRESS.md`](PROGRESS.md). Empieza por ahí.
`.claude/settings.json` bloquea `git commit`, `git push` y los comandos `az`/`azcopy`: los commits los hace una persona.

## Licencia

[MIT](LICENSE).
