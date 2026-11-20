---
name: eda-spotify
description: Hacer o rehacer el EDA del Spotify Global Music Dataset (2009-2025, Kaggle wardabilal) de este repo con Polars, QA que falla ruidosamente y notebook versionado. Úsala cuando pidan EDA, calidad de datos, versión v2 del notebook, gráficos o tablas de este dataset, o cargarlo para el buscador semántico.
---

# EDA del Spotify Global Music Dataset

Base ya existente: `src/spotify_eda.py` (módulo reutilizable), `notebooks/01_eda_spotify_v1.ipynb`,
salidas en `artifacts/figures` (E* = decisores, T* = técnico) y `artifacts/tables`. **Reutiliza el módulo; no reescribas.**
Marca como **POR VERIFICAR** todo lo que no hayas medido; nunca inventes cifras.

## Flujo (celdas numeradas `[N] TÍTULO` en el notebook)

0. Portada: qué es, qué cambia respecto a la versión anterior, decisión de fuente, criterio de "hecho".
1. Configuración: `se.Config()` (dataclass frozen) + `se.apply_style(cfg)`. Todo parámetro vive ahí.
2. Carga: `download_raw` (kagglehub → copia en `data/raw`) y `read_raw_strings` (texto puro).
3. QA entrada = salida: `run_qa` (ida y vuelta por columna, unicidad/orden de `track_id`, rangos, regrupar géneros).
4. Hallazgos por severidad (crítico/alto/medio/bajo) con `filas` y `pct`.
5. Distribuciones numéricas (técnico), 6. categorías/nombres/géneros, 7. sección para decisores,
8. verificación contra el otro CSV, 9. exportación + QA de salida, 10. "Cómo leer los resultados".

Ejecutar el notebook: `uv run jupyter nbconvert --to notebook --execute --inplace notebooks/<archivo>.ipynb`
(o con `nbclient`). Versionar como `02_eda_spotify_v2.ipynb`, no pisar la v1.

## Hechos del dataset (verificados en el EDA v1)

- Fuente `wardabilal/spotify-global-music-dataset-20092025`. Principal: `track_data_final.csv` (8 778 canciones,
  15 columnas, 2 548 artistas, 5 317 álbumes, 423 géneros). `spotify_data clean.csv` (8 582) es **subconjunto estricto**: úsalo solo para verificar.
- Sin letras ni audio features. Es una muestra, no el catálogo (método de muestreo: POR VERIFICAR).
- **No hay `artist_id`**: la identidad es el nombre (homónimos POR VERIFICAR).
- El género es del **artista** y falta en ~51 % de canciones. Atributos de artista se repiten por canción:
  agregar **por artista** (`build_artists`), no promediar por canción (sobre-pondera a los prolíficos).
- ~17,6 % de canciones comparten artista+título (single/álbum/reedición).
- La fecha es la del **álbum**, con precisión variable (`day|month|year`); ~16 % cae fuera de 2009–2025 y hay `0000`.
- Hay duraciones de 0 ms (placeholder) y popularidad 0: se reportan, se excluyen donde distorsionan, nunca se borran en silencio.

## Trampas ya resueltas (no las repitas)

- **Polars rompe con comillas sin escapar** (p. ej. `The 12" Singles`): leer con el módulo `csv` y construir
  el DataFrame con esquema; verificar que cada fila tenga el mismo número de campos que el header.
- Esquema explícito, nunca todo a texto: `album_type` es `pl.Enum`, `artist_popularity`/`followers` llegan como
  `"80.0"` → `Float64` y luego `Int`. Vacío → `null`.
- `artist_genres` es un string con una lista Python → `ast.literal_eval` (no `eval`).
- `0000` en fecha → `release_year` nulo + hallazgo.
- **Consola Windows cp1252**: imprimir con `PYTHONIOENCODING=utf8` o forzar `stdout` UTF-8; si no, falla con tildes y flechas.
- Los notebooks guardan tildes en UTF-8; leerlos con `encoding="utf8"`.
- Python ≥ 3.14, entorno con `uv` (`.venv`). Dependencias: polars, pyarrow, kagglehub, matplotlib, seaborn, nbclient/nbconvert.

## Reglas de calidad (del repo)

- Controles que **fallan ruidosamente** (`assert`); sin `try/except` que oculte errores.
- Toda tabla agregada que alimenta un gráfico pasa por `assert_partition(tabla, col, total, etiqueta)`.
- `save_fig` verifica que el PNG no esté vacío. Estilo único vía `apply_style`; paleta en `cfg.colors`.
- Números que signifiquen lo que dicen: revisar nombre de columna vs contenido, comparar géneros solo con
  `min_genre_tracks` (30) canciones, avisar de sesgo de muestreo.
- Exportar a `artifacts/` (CSV/parquet) y cerrar con "Cómo leer los resultados".
- Sin commits (los hace el usuario); limpiar temporales; nada a Azure/nube sin OK explícito.

## Para el buscador semántico (ver `SPEC.md`)

El EDA alimenta la capa plata: `build_typed` / `explode_genres` / `build_artists` migran a módulos de `src/`;
`data/raw` → `bronze`, `data/processed` → `silver`. Texto indexable solo de metadatos (nombre, artista, álbum, géneros, año).
Agrupar versiones por artista+título normalizados al mostrar resultados.
