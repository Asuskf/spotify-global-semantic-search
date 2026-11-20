# PROGRESS.md — handoff entre sesiones

Última actualización: 2026-11-19 (revisión del repo). Se escribe al cerrar cada sesión, desde `feature_list.json` y la salida real de `scripts/check.sh`, no de memoria.

## Completado (verificado)
- F01 bronce, F02 plata, F03 oro, F04 API, F06 compose: ver evidencia en `feature_list.json`.
- F12/F13/F05: la UI se rediseñó con la identidad SEVEN TECH y la suite E2E pasa: `cd e2e && npx playwright test` → **24 passed** (6 de contrato de API + 18 de UI) contra el stack real; vista revisada en escritorio y a 375 px.
- Revisión del repo (2026-11-19), ver `DECISIONS.md`: el manifiesto se revoca antes de sobrescribir plata/oro y no se escribe si falta documentar una columna; bronce compara el origen aunque falte su CSV; la API exige el manifiesto de oro (503) y que existan sus archivos (error con la ruta); los ejemplos se deshabilitan mientras carga. Revisado por un subagente de solo lectura. Imágenes reconstruidas (`docker compose up -d --build` y `spotify-dev`).
- Verificación de cierre: pytest en Docker **30 passed**; `scripts/check.sh --e2e` OK (10 passed/20 skipped local + `/api/health` + búsqueda real + 24 E2E passed).
- Para otro desarrollador: `README.md`, `scripts/init.sh` (clon limpio → stack), `.gitignore` (datos generados fuera de git, conjunto dorado dentro), `.claude/settings.json` (deny de commit/push/Azure).
- EDA v1 (`notebooks/01_eda_spotify_v1.ipynb`): 27 controles de QA y 14 figuras en `artifacts/figures/`.

## Roto o sin verificar
- F11 (la única `active`): la copia limpia del ensayo tiene los tres manifiestos con el QA en verde, pero no se vio la salida de `init.sh --sin-stack`, no se sabe si kagglehub pidió credenciales y no se corrió `docker compose` + `check.sh` desde esa copia (POR VERIFICAR).
- Calidad semántica **POR VERIFICAR**: el conjunto dorado (25 consultas) no tiene etiquetas; `src.eval` no se ha ejecutado. No afirmar que el semántico supera a BM25.
- Sin logo oficial (F14): falta `logo-seventech.png` en la skill de marca; la UI usa el wordmark de texto.
- Sin probar: Safari/Firefox, lector de pantalla, latencia por consulta, reproducibilidad del índice (F10), agrupación de versiones con consultas reales, linaje por fila (F09).
- Sin CI. `git_dirty` sale en true en los manifiestos hasta que haya commits.
- La imagen de la API pesa 2,34 GB; el volumen `hf_cache` guarda más de lo necesario (se puede borrar y regenerar).

## Siguiente mejor paso
1. Cerrar F11: en la copia limpia, `docker compose up -d --build` + `scripts/check.sh`, y confirmar lo de las credenciales de Kaggle.
2. F10 sale barato después: la copia del ensayo tiene un segundo `embeddings.npy` para comparar con el de referencia (coseno ≥ 0.9999).
3. Decidir quién etiqueta el conjunto dorado (desbloquea F07 y F08) y si se aporta el logo (F14).
4. Pendiente menor: rehacer plata no invalida el manifiesto de oro (ver `DECISIONS.md`).

## Decisiones tomadas
Ver `DECISIONS.md` (hnswlib en Docker, e5-base, alcance v1, medallón, duplicados, géneros omitidos, init.sh y datos fuera de git, deny de commit/push/Azure, identidad SEVEN TECH, manifiesto revocado antes de sobrescribir, ejemplos deshabilitados al cargar).
