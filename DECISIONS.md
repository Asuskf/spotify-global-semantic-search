# DECISIONS.md — lo que la compactación pierde (el porqué)

Formato: decisión · motivo · alternativa rechazada · restricción. Nuevas decisiones se agregan arriba.

## 2026-11-19: El manifiesto se revoca antes de sobrescribir una capa; la API exige el manifiesto de oro
- Motivo (revisión del repo): `silver()`/`gold()` sobrescribían los archivos y, si el QA fallaba después, el manifiesto viejo seguía certificando archivos que ya no describía; `init.sh` lo daba por bueno y la API servía el índice. Ahora `_revoke()` borra `_manifest.json` antes de escribir, y `_load()` devuelve 503 si falta el manifiesto (antes miraba solo `hnsw.index`).
- Bronce no lo necesita: es write-once y falla antes de escribir. Sí se cerró otro hueco: si se borraba un CSV de bronce, se copiaba el origen actual sin compararlo con el manifiesto; ahora el origen se compara siempre.
- `_finish` valida el diccionario de datos (`CATALOG`) ANTES de escribir manifiesto y linaje: antes una columna sin documentar dejaba la capa certificada y luego fallaba.
- La API comprueba que existan las salidas del manifiesto antes de cargar el modelo y falla con la ruta (hnswlib solo decía "Cannot open file" y el contenedor quedaba en bucle de reinicios).
- Hallazgos de la revisión por subagente de solo lectura (regla 11); cada uno con su prueba.
- Restricción: tras un QA fallido hay que volver a correr la capa (init.sh ya lo hace solo, porque mira el manifiesto). Pendiente: rehacer plata no invalida oro (el manifiesto de oro puede citar un SHA de plata que ya no existe).
- Alternativa rechazada: escribir en una carpeta temporal y renombrar al pasar el QA (más código para el mismo resultado en un demo).

## 2026-11-19: Los ejemplos de búsqueda se deshabilitan mientras carga
- Motivo: el botón Buscar ya se deshabilitaba, pero un clic en otro ejemplo lanzaba una segunda búsqueda y la respuesta más lenta podía pisar a la nueva. Cubierto en la E2E de "estado de carga".

## 2026-11-19: Un desarrollador nuevo arranca con `scripts/init.sh`; los datos generados no se versionan
- Motivo: el usuario pidió poder ejecutar el repo sin esta sesión. `bronze` solo leía `data/raw` (creado antes por el notebook del EDA), así que un clon nuevo no arrancaba: `init.sh` descarga los CSV con kagglehub.
- Decisión: `.gitignore` excluye `data/*` salvo `data/gold/eval/` (el conjunto dorado es fuente, no salida), y `node_modules`. El CSV de Kaggle no se redistribuye (licencia POR VERIFICAR).
- Alternativa rechazada: versionar `data/gold` (54 MB de binarios, regenerables en ~16 min).

## 2026-11-19: `.claude/settings.json` bloquea `git commit`, `git push`, `az` y `azcopy`
- Motivo: "sin commits" y "nada a Azure" son reglas sin excepción; la skill buenas-practicas pide imponerlas con `deny`, no con texto.
- Restricción: si algún día se quiere que Claude haga commits, hay que quitar esa línea.

## 2026-11-19: UI con la identidad SEVEN TECH; E2E con Playwright solo en Chromium
- Motivo: el usuario pidió que la web siga `brand-guidelines-seventech` (con impeccable y ui-ux-pro-max) y pruebas E2E con playwright-skill/webapp-testing.
- Choque marca/impeccable: ganó la marca; se omitió gradiente sobre texto y kicker. Peso 850 en vez de 950 (la Inter variable llega a 900).
- Sin logo oficial (no vino en el `.skill`): wordmark de texto. E2E en `e2e/` con su propio `package.json` para no mezclar Playwright con las dependencias del front.

## 2026-11-19: HNSW con hnswlib, solo dentro de Docker
- Motivo: el usuario lo eligió (la SPEC §6 lo proponía; faiss-cpu era la alternativa).
- Alternativa rechazada: faiss-cpu (ya implementado y probado, corría en Windows y Docker). Se descartó por preferencia del usuario.
- Restricción: hnswlib no compila en Windows (falta Visual Studio); oro y 20 de 30 pruebas corren solo en Docker.

## 2026-11-19: Modelo de embeddings `intfloat/multilingual-e5-base`
- Motivo: multilingüe (consultas en español, metadatos en inglés), cabe en CPU sin GPU. Recall@10 real del HNSW 0.9905.
- Alternativas rechazadas: e5-small (menos calidad), bge-m3 (más pesado). Comparar en un benchmark sigue pendiente.
- Restricción: descarga ~1 GB; se autorizó explícitamente. Pesos en el volumen `spotify-global-semantic-search_hf_cache`.

## 2026-11-18: Alcance v1 = búsqueda semántica pura
- Motivo: demo de portafolio/curso; menos piezas, más reproducible.
- Rechazado para v1: filtros, búsqueda híbrida, "más como esta", descripciones generadas por LLM, imputación de géneros.
- BM25 existe solo como baseline de evaluación.

## 2026-11-18: Texto indexado solo con metadatos; campo nulo se omite
- Motivo: determinista y verificable; el género falta en el 51 % de las canciones y no se inventa ni se imputa.
- Alternativas rechazadas: "unknown genre" (ruido idéntico en la mitad del catálogo), heredar género del artista (imputación sin validar).

## 2026-11-18: Duplicados: indexar todo, agrupar al mostrar
- Motivo: el índice sigue siendo 1:1 con el dataset (el QA lo exige); la API colapsa versiones del mismo artista+título normalizados.
- Alternativa rechazada: deduplicar antes de indexar (rompe el 1:1 y obliga a elegir una versión).

## 2026-11-18: Arquitectura medallón con manifiestos y linaje
- Motivo: el usuario pidió poder reproducir cada paso con metadatos y linaje.
- Restricción: bronce write-once con SHA-256; manifiesto solo si el QA pasa; vectores se validan por tolerancia, no por bytes.

## 2026-11-18: Stack: Flask + React (Vite, JS) + Docker Compose
- Motivo: pedido del usuario. Front en `web/` (excepción a `src/`: proyecto Node con su Dockerfile).
- Rechazado: Streamlit/Gradio, FastAPI.

## 2026-11-17: Dos CSV en Kaggle; fuente única `track_data_final.csv`
- Motivo: contiene los 8 582 de `spotify_data clean.csv` más 196 más, y conserva duración en ms y géneros como lista.
- Restricción: polars no parsea el CSV (comillas sin escapar); se lee como texto con `csv` y se tipa después.

## 2026-11-17: Entorno con uv, Python local 3.14, imagen Docker con Python 3.12
- Motivo: ruedas de torch/hnswlib para cp312 resueltas; el local usa 3.14.
