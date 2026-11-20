# spotify-global-semantic-search

Buscador semántico de canciones: frase en lenguaje natural → canciones más similares del Spotify Global Music Dataset
(Kaggle `wardabilal/spotify-global-music-dataset-20092025`, 8 778 canciones). Demo de portafolio, reproducible.
Pipeline medallón (bronce/plata/oro) → embeddings `multilingual-e5-base` → HNSW (hnswlib) → API Flask → front React, en Docker Compose.

## Antes de nada (clock in)
1. Lee `PROGRESS.md` (dónde estamos) y `DECISIONS.md` (el porqué). 2. Corre `scripts/check.sh`: si la base está rota, **se arregla primero**.
3. Toma la única feature `active` de `feature_list.json` (WIP = 1). Lo adyacente se anota como pendiente, no se toca.

## Arrancar desde cero
`scripts/init.sh` (clon limpio → datos → oro en Docker → stack en :8080; idempotente). Guía humana en `README.md`.

## Verificar (el "hecho" es un comando)
```bash
scripts/check.sh              # pytest local + /api/health + una búsqueda real (stack en :8080); --sin-stack omite el stack; --e2e suma Playwright
(cd e2e && npx playwright test)  # 24 pruebas E2E contra http://localhost:8080 (E2E_BASE_URL cambia la URL)
docker build -f docker/api.Dockerfile --target dev -t spotify-dev .
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/work" spotify-dev python -m pytest -q -p no:cacheprovider   # las 30 pruebas
```
"Hecho" = el comando pasó y pegaste su salida real. Solo la verificación pasa una feature a `passing`; el agente no la marca por su cuenta.

## Correr
```bash
uv run python -m src.pipeline bronze|silver        # local. Oro: SOLO en Docker (hnswlib no compila en Windows):
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/work" -v spotify-global-semantic-search_hf_cache:/root/.cache/huggingface spotify-dev python -m src.pipeline gold
docker compose up -d --build                        # front http://localhost:8080 · estado en /api/health
PYTHONIOENCODING=utf-8 uv run jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda_spotify_v1.ipynb
```

## Mapa (lee según la tarea, no todo)
| Qué | Dónde |
|---|---|
| Qué, por qué y criterios de aceptación | `SPEC.md` · estado: `feature_list.json`, `PROGRESS.md` · porqués: `DECISIONS.md` |
| Plata: carga, tipado, hallazgos, QA | `src/spotify_eda.py` |
| Pipeline y manifiestos/linaje | `src/pipeline.py` · `data/{bronze,silver,gold,_lineage,_catalog}` |
| Encoder e5 (prefijos `passage: `/`query: `) | `src/encoder.py` |
| API Flask · evaluación BM25 | `src/api/app.py` · `src/eval.py`, `data/gold/eval/golden_queries.json` |
| Front React (leer al tocar la UI) | `web/` (`web/DESIGN.md`; `web/mock-api.mjs` = API simulada) · E2E: `e2e/` |
| Imágenes y servicios | `docker/api.Dockerfile`, `web/Dockerfile`, `docker-compose.yml` |
| EDA v1 (usa `data/raw` y `data/processed`; **no borrar**) | `notebooks/`, `artifacts/` |
| Skills | `ponytail` (activa), `harness-prompting`, `buenas-practicas-claude-code`, `langgraph`, `eda-spotify`, `webapp-testing` y `playwright-skill` (E2E del front), `brand-guidelines-seventech` (identidad de la UI, manda sobre las demás), `impeccable` y `ui-ux-pro-max` (craft, al tocar `web/`) |

## Reglas duras (si se rompen, algo debe fallar)
1. **Entrada = salida**: cada capa valida filas, ids y orden; el manifiesto se escribe solo si el QA pasa. Debilitar un control para que "pase" no es corregir.
2. **Bronce inmutable** (write-once, SHA-256). **Nada se borra en silencio**: anomalías → `findings`; vacío → null, nunca inventado.
3. **Contrato de la API fijo** (`/health`, `/search` con `query` y `k` 1–50, errores `{"error": ...}` en español). Si cambia: `web/`, pruebas y `SPEC.md §7` en el mismo cambio.
4. **Una sola fuente del texto indexado**: plantilla de `SPEC.md §4`; campo nulo se omite.
5. Controles y errores **fallan ruidosamente**; nada de `try/except` que oculte un fallo. Mensajes con qué falló, por qué y cómo arreglarlo.
6. Toda salida nueva agrega su línea a `lineage.jsonl` y su columna al diccionario.
7. Prohibido debilitar pruebas o reescribir `feature_list.json` para ocultar trabajo pendiente.
8. Lo no verificado se marca **POR VERIFICAR**; nunca se inventan cifras, etiquetas ni referencias. No afirmar que el semántico supera a BM25 sin `src.eval` con el dorado **etiquetado**.
9. El front mantiene el contrato de `data-testid` que usa `e2e/` (ver `web/DESIGN.md`/`e2e/tests/ui.spec.ts`); cambiar la UI sin correr la suite no es "hecho".
10. Estilo `ponytail`: el cambio más pequeño que resuelve el problema completo; un atajo con límite lleva `# shortcut: <límite>, <cuándo mejorar>`.
11. Cada lógica nueva no trivial deja su prueba; quien implementa no se juzga solo: la revisión la hace otro (subagente de solo lectura o `/code-review`).

## Gotchas
- Windows cp1252: `PYTHONIOENCODING=utf-8`. Polars no parsea el CSV (comillas sin escapar): se lee con `csv` y se tipa después.
- En Git Bash anteponer `MSYS_NO_PATHCONV=1` a `docker run` con rutas. Docker Desktop debe estar corriendo; la API tarda ~30 s en quedar healthy.
- Género y popularidad de artista son del **artista**; la fecha es la del **álbum**; no hay `artist_id` (identidad = nombre).
- El volumen `spotify-global-semantic-search_hf_cache` guarda los pesos del modelo; no se vuelve a descargar si existe.

## Al cerrar (clock out)
- [ ] `scripts/check.sh` pasa y pegaste su salida · [ ] `feature_list.json` y `PROGRESS.md` actualizados desde la salida real · [ ] decisiones del chat pasadas a `DECISIONS.md`
- [ ] Sin temporales, `__pycache__` ni código de debug · [ ] El stack sigue arrancando con `docker compose up -d`.
- **Sin commits**: los hace el usuario. Nada a Azure ni a otra nube sin OK explícito. Descargas pesadas (modelos, datasets) solo con permiso explícito.
