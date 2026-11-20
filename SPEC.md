# SPEC · Buscador semántico sobre Spotify Global Music Dataset (2009–2025)

Estado: borrador v1 para aprobar · Fecha: 2026-11-18
Marcas: lo que no está verificado va como **POR VERIFICAR**; las cifras de esta spec son propuestas o salen del EDA v1, nunca de mediciones del buscador (todavía no existe).

## 1. Objetivo y alcance

Demo de portafolio / curso, reproducible de punta a punta: el usuario escribe una frase en lenguaje natural (español o inglés) y obtiene las canciones más similares del dataset.

Dentro de la v1:
- **Búsqueda semántica pura** (frase → top-k canciones con puntaje de similitud).
- Pipeline de datos en **arquitectura medallón (bronce / plata / oro)** con metadatos y linaje en cada paso.
- Índice **HNSW en memoria** dentro del backend.
- Backend **Flask**, frontend **React**, todo con **Docker Compose**.
- QA de integridad, conjunto dorado de consultas, pruebas de API/compose y revisión visual manual.

Fuera de la v1 (decidido en la entrevista): filtros estructurados, búsqueda híbrida con BM25 como función, "más como esta", descripciones generadas por LLM, imputación de géneros, autenticación, cualquier despliegue en la nube (regla del repo: nada a Azure sin OK explícito).
BM25 **sí** existe, pero solo como baseline de evaluación (sección 8).

## 2. Datos de partida (hechos del EDA v1)

- Fuente: Kaggle `wardabilal/spotify-global-music-dataset-20092025`, archivo principal `track_data_final.csv`: 8 778 canciones, 2 548 artistas, 5 317 álbumes, 423 géneros. `spotify_data clean.csv` (8 582) es un subconjunto estricto del principal.
- Sin letras ni audio features: el texto indexable sale solo de metadatos.
- El género es del **artista** y falta en el 51 % de las canciones (4 496).
- El 17,6 % de las canciones comparten artista+título (misma canción en single/álbum/reedición).
- La fecha es la del **álbum**; el 16 % cae fuera de 2009–2025.
- No hay `artist_id`: la identidad de artista es el nombre (homónimos **POR VERIFICAR**).
- Es una muestra, no el catálogo de Spotify (cómo se muestreó: **POR VERIFICAR**).

## 3. Arquitectura medallón

Principio: **cada capa se escribe una vez por corrida, es reproducible desde la capa anterior y declara de dónde viene.** Nada se elimina en silencio: las anomalías se marcan, no se borran.

```
data/
  bronze/            # inmutable: lo que llegó, tal cual
    track_data_final.csv
    spotify_data clean.csv
    _manifest.json
  silver/            # limpio, tipado, 1 fila = 1 entidad
    tracks.parquet
    artists.parquet
    track_genres.parquet
    _quality/findings.parquet
    _manifest.json
  gold/              # listo para servir
    search_docs.parquet
    embeddings.npy  +  embedding_ids.parquet
    hnsw.index
    version_groups.parquet
    _manifest.json
  _lineage/lineage.jsonl          # append-only, una arista por salida
  _catalog/data_dictionary.yaml   # diccionario y linaje a nivel columna
```

(`data/raw` y `data/processed` del EDA v1 migran a `bronze` y `silver`.)

### 3.1 Bronce — "lo que llegó"
- Copia **byte a byte** de los dos CSV descargados con `kagglehub`. Sin parseo, sin renombrar columnas.
- Solo escritura única: si el archivo existe y su SHA-256 difiere del manifiesto, **falla** (no sobrescribe).
- `_manifest.json` registra: slug de Kaggle, versión del dataset que devolvió kagglehub, fecha/hora UTC de descarga, nombre original, bytes, SHA-256, número de registros contados con un lector CSV independiente.

### 3.2 Plata — "limpio y tipado"
- Es el `build_typed` / `explode_genres` / `build_artists` del EDA v1, movido a módulos de `src/`: lectura como texto con el módulo `csv`, esquema explícito, vacío → null, fecha con precisión (`day|month|year`), `release_year` nulo para `0000`, géneros como lista.
- Tablas: `tracks` (8 778 filas, 1:1 con bronce), `artists` (1 por nombre), `track_genres` (larga).
- `findings.parquet`: los hallazgos por severidad del EDA (artista vacío, sin género, fuera de ventana, duración 0 ms, etc.), con `track_id` por hallazgo para poder auditarlos.
- QA de plata (falla ruidosamente): los 27 controles del EDA v1 (conteos, ida y vuelta por columna, unicidad y orden de `track_id`, rangos imposibles, regrupar géneros == lista original).

### 3.3 Oro — "listo para servir"
- `search_docs`: una fila por canción con `doc_text` (plantilla, sección 4), `template_version`, `text_hash`.
- `embeddings.npy` (float32, N×768, normalizados L2) y `embedding_ids.parquet` (mismo orden que `search_docs`).
- `hnsw.index`: índice HNSW sobre esos vectores, con sus parámetros en el manifiesto.
- `version_groups`: `group_id` por artista+título normalizados (minúsculas, espacios colapsados) para agrupar versiones al mostrar.
- QA de oro: ver sección 8.

### 3.4 Metadatos y linaje (obligatorio en cada capa)

**`_manifest.json` por capa** (esquema común):

| Campo | Contenido |
|---|---|
| `layer`, `run_id` | capa y corrida (`UTC-timestamp + hash corto de git`) |
| `created_utc` | cuándo se generó |
| `code` | módulo/función que lo produjo, `git_commit`, `git_dirty` |
| `params` | parámetros que afectan el resultado (plantilla, modelo, M, ef, …) |
| `inputs[]` | ruta, SHA-256, filas y `run_id` de la capa de origen |
| `outputs[]` | ruta, SHA-256, filas, bytes, esquema (columna → tipo) |
| `qa[]` | cada control con su resultado (el manifiesto no se escribe si alguno falla) |
| `env` | versiones de Python y de las librerías relevantes |

**`lineage.jsonl`** (append-only): una línea por salida con `output`, `inputs`, `transformation`, `run_id`. Permite recorrer el grafo bronce → plata → oro y responder "¿de qué CSV y qué código salió este vector?".

**`data_dictionary.yaml`**: por columna de plata y oro: tipo, nulabilidad y su significado (con la aclaración de que género y popularidad de artista son atributos del artista, y la fecha es la del álbum), y `derived_from` (columna(s) origen). Ejemplo: `search_docs.doc_text ← tracks.{track_name, artist_name, album_name, album_type, release_year, explicit}, track_genres.genre`.

**Cada fila de oro** conserva `track_id` y puede reconstruirse hasta su fila de bronce; el manifiesto de oro guarda además el modelo de embeddings con su **revisión exacta** (commit de HuggingFace, leída en tiempo de ejecución).

### 3.5 Reproducibilidad
- Un comando por capa y uno para todo (`bronze`, `silver`, `gold`, `all`), con `uv run`.
- Plata es **determinista**: misma entrada ⇒ mismas filas y valores (se compara por contenido, no por bytes del parquet).
- Oro: los textos son deterministas; los vectores pueden diferir por hardware/versión de librería, así que la reproducción se valida por **tolerancia** (similitud coseno ≥ 0,9999 contra la corrida de referencia; umbral propuesto, **POR VERIFICAR**) y el HNSW se reconstruye con semilla fija.
- Re-ejecutar una capa cuyo manifiesto de entrada no cambió no la recalcula; si el SHA-256 de entrada cambió, la capa se invalida y los pasos siguientes también.

## 4. Texto que se embebe

Una plantilla fija y versionada (`template_version`), solo con metadatos:

`Canción: {track_name}. Artista: {artist_name}. Álbum: {album_name} ({album_type}). Año: {release_year}. Géneros: {géneros}. Contenido explícito.`

Reglas:
- Campo nulo ⇒ **se omite** la frase completa (no se escribe "unknown"). Sin género ⇒ no se menciona género; el front muestra "sin género".
- "Contenido explícito." solo si `explicit` es verdadero.
- Con el modelo e5 se usa el prefijo `passage: ` al indexar y `query: ` al consultar (convención documentada del modelo; **POR VERIFICAR** contra su ficha).
- Sin imputación ni textos generados: lo que se indexa es lo que dice el dato.

## 5. Modelo de embeddings

- Por defecto: `intfloat/multilingual-e5-base` (768 dimensiones). Alternativas a comparar en un benchmark corto: `multilingual-e5-small` y `BAAI/bge-m3`.
- CPU (i7-13700H, 24 GB, sin GPU CUDA). Tiempos y tamaños de memoria: **POR VERIFICAR** con el benchmark (se reportan medidos, no estimados).
- Los vectores se calculan **offline** en la capa oro; el contenedor de la API solo carga el modelo para codificar la consulta.

## 6. Índice HNSW

- Librería propuesta: `hnswlib` (alternativa: FAISS HNSW). Disponibilidad de ruedas para la versión de Python elegida: **POR VERIFICAR**.
- Métrica: coseno (vectores normalizados, producto interno).
- Parámetros iniciales propuestos: `M=16`, `ef_construction=200`, `ef_search=50`; se ajustan con el benchmark y quedan registrados en el manifiesto.
- Se carga una vez al arrancar Flask y vive en memoria; el archivo `hnsw.index` viene del oro (montado de solo lectura).

## 7. API, front y Docker

**API (Flask, servida con gunicorn)**
- `GET /health` → estado, versión de modelo, número de vectores, `run_id` de oro.
- `POST /search` con `{"query": str, "k": int}` (k por defecto 10, máximo propuesto 50).
- Respuesta: lista de resultados con `track_id`, título, artista, álbum, año, géneros (o vacío), popularidad, explícito, puntaje de similitud y `otras_versiones[]`. Las versiones de un mismo `group_id` se colapsan en una sola tarjeta (se muestra la de mayor similitud); el índice sigue teniendo las 8 778 filas.
- Errores explícitos: consulta vacía o demasiado larga → 400 con mensaje; índice no cargado → 503. Nada de `try/except` que oculte fallos.

**Front (React, español)**
- Caja de búsqueda, consultas de ejemplo clicables, tarjeta por resultado con título, artista, álbum, año, géneros ("sin género" si no hay), popularidad, marca de explícito, puntaje y "otras versiones".
- Estados de carga, vacío y error visibles. Responsive.

**Docker Compose**
- Servicios: `api` (Flask + modelo + HNSW) y `web` (build de React servido por nginx, con proxy a `/api`).
- `data/gold` se monta de solo lectura en `api`; los pesos del modelo van en un volumen de caché para no descargarse en cada arranque.
- `docker compose up` desde cero deja el sistema respondiendo, con un paso previo documentado para generar el oro (`uv run … all`).
- Versión de Python de la imagen: **POR VERIFICAR** (el entorno local usa 3.14; si `hnswlib`/`torch` no tienen ruedas, la imagen usa 3.12 y se documenta).

**Estructura del repo** (se mantiene `src / data / notebooks`): `src/` (pipeline y `src/api`), `data/`, `notebooks/`, y `web/` en la raíz para el front React (excepción justificada: es un proyecto Node con su propio Dockerfile).

## 8. QA y criterios de aceptación

La v1 está **hecha** cuando todo lo siguiente pasa:

1. **Integridad del índice (entrada = salida).**
   - bronce: SHA-256 y conteo de registros coinciden con el manifiesto;
   - plata: los 27 controles del EDA v1;
   - oro: `search_docs` = `tracks` en filas, `track_id` y orden; `embedding_ids` == `search_docs.track_id`; matriz N×768 sin NaN y norma ≈ 1; el índice HNSW contiene N elementos; los textos se regeneran y coinciden con `text_hash`;
   - **recall del HNSW** contra búsqueda exacta (fuerza bruta) ≥ umbral propuesto de 0,95 en recall@10 sobre consultas de prueba (**umbral POR VERIFICAR**, se mide).
2. **Linaje consultable.** Para 5 `track_id` elegidos al azar se recorre `lineage.jsonl` desde un vector hasta la fila de bronce, sin huecos.
3. **Conjunto dorado.** ~25 consultas escritas a mano (español e inglés; géneros, época, ánimo, artista, tipo de álbum), cada una con los `track_id` relevantes. Métricas: recall@10 y nDCG@10 del buscador semántico **contra un baseline BM25** sobre los mismos `doc_text`. Quién etiqueta lo relevante: **POR DEFINIR**. Sin afirmar que el semántico mejora al BM25 hasta verlo en estas métricas.
4. **Pruebas de API y compose.** Tests de `/health` y `/search` (casos válidos, vacío, k fuera de rango, agrupación de versiones); `docker compose up` desde cero responde en `/health` y desde el front.
5. **Revisión manual visual.** Recorrido en el navegador con las consultas de ejemplo, registrado con capturas.

## 9. Entregables

- `src/`: módulos de bronce, plata, oro, linaje, QA y API; CLI por capa.
- `web/`: app React. `docker-compose.yml` y Dockerfiles.
- `data/{bronze,silver,gold,_lineage,_catalog}`.
- `notebooks/`: EDA v2 (mismos controles, rutas a las nuevas capas) y notebook de evaluación (benchmark de modelos, conjunto dorado, recall del HNSW).
- `artifacts/`: tablas y figuras de la evaluación; sección final "Cómo leer los resultados".
- `README.md` con uso y Docker.

## 10. Riesgos y supuestos

- **Metadatos pobres**: sin letras ni audio, "ánimo" o "estilo" solo se infiere de géneros/títulos; el 51 % sin género limita las consultas por género.
- **Sesgo de muestra**: artistas muy presentes (p. ej. uno con 330 canciones) dominarán algunos resultados; los rankings reflejan el dataset, no el mercado.
- **Contaminación/foto temporal**: la popularidad es una foto de un momento no verificado.
- **Dependencias en CPU y Python 3.14**: ruedas de `torch`/`hnswlib` **POR VERIFICAR**.
- **Licencia del dataset y de los modelos**: **POR VERIFICAR** antes de publicar el demo.

## 11. Preguntas abiertas

1. ¿Quién etiqueta los resultados relevantes del conjunto dorado?
2. ¿Python 3.12 en Docker si no hay ruedas para 3.14?
3. ¿Umbrales finales de recall del HNSW y de coseno para reproducir vectores (hoy propuestos)?
4. ¿`web/` en la raíz está bien o prefieres todo bajo `src/`?
