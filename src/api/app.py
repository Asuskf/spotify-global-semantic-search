"""API Flask del buscador semantico. Servir con:  gunicorn "src.api.app:create_app()"

Carga modelo e indice UNA vez al arrancar desde GOLD_DIR. Errores explicitos: 400 / 503.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import numpy as np
import polars as pl
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from src.encoder import QUERY_PREFIX

MAX_QUERY_CHARS = 300  # propuesta de la SPEC
MAX_K = 50


def _load(gold: Path, encoder):
    """Devuelve el estado (indice, tarjetas, grupos, encoder) o None si el oro no esta certificado.
    Manda el manifiesto, no el indice: una corrida de oro con QA fallido deja archivos pero no manifiesto."""
    if not (gold / "_manifest.json").exists():
        return None
    manifest = json.loads((gold / "_manifest.json").read_text(encoding="utf-8"))
    # antes de cargar el modelo (~1 GB): hnswlib solo diria "Cannot open file", sin ruta
    missing = [Path(o["path"]).name for o in manifest["outputs"] if not (gold / Path(o["path"]).name).exists()]
    assert not missing, f"oro certificado pero faltan {missing} en {gold}: borra {gold / '_manifest.json'} y vuelve a correr gold"
    info = manifest["params"]["model"]
    if encoder is None:
        from src.encoder import load_st
        encoder = load_st(info["name"])[0]
    import hnswlib  # import tardio: solo existe en Linux/Docker

    docs = pl.read_parquet(gold / "search_docs.parquet")
    index = hnswlib.Index("cosine", info["dim"])
    index.load_index(str(gold / "hnsw.index"), max_elements=docs.height)
    groups = pl.read_parquet(gold / "version_groups.parquet")
    assert index.get_current_count() == docs.height == groups.height, "indice, search_docs y version_groups no coinciden"
    return {
        "ef": manifest["params"]["hnsw"]["ef_search"], "index": index, "lock": threading.Lock(), "encode": encoder, "model": info["name"], "run_id": manifest["run_id"],
        "rows": docs.to_dicts(), "group": groups["group_id"].to_list(),
    }


def create_app(gold_dir: str | Path | None = None, encoder=None) -> Flask:
    """`encoder`: funcion list[str] -> ndarray normalizado (inyectable en pruebas)."""
    app = Flask(__name__)
    app.json.ensure_ascii = False
    state = _load(Path(gold_dir or os.environ.get("GOLD_DIR", "data/gold")), encoder)

    def err(msg: str, code: int):
        return jsonify({"error": msg}), code

    @app.errorhandler(HTTPException)
    def http_error(e):
        return err({404: "Ruta no encontrada.", 405: "Método no permitido."}.get(e.code, e.description), e.code)

    @app.get("/health")
    def health():
        if state is None:
            return err("El índice no está cargado: falta generar la capa oro.", 503)
        return jsonify(status="ok", model=state["model"], n_vectors=state["index"].get_current_count(), gold_run_id=state["run_id"])

    @app.post("/search")
    def search():
        if state is None:
            return err("El índice no está cargado: falta generar la capa oro.", 503)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return err("El cuerpo debe ser un JSON válido con la forma {\"query\": texto, \"k\": entero}.", 400)
        query, k = body.get("query"), body.get("k", 10)
        if not isinstance(query, str) or not query.strip():
            return err("La consulta no puede estar vacía.", 400)
        if len(query.strip()) > MAX_QUERY_CHARS:
            return err(f"La consulta es demasiado larga (máximo {MAX_QUERY_CHARS} caracteres).", 400)
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= MAX_K:
            return err(f"k debe ser un entero entre 1 y {MAX_K}.", 400)

        query = query.strip()
        q = np.asarray(state["encode"]([QUERY_PREFIX + query]), dtype="float32")[:1]
        index, group, rows = state["index"], state["group"], state["rows"]
        n = index.get_current_count()
        kk = min(k * 4, n)
        while True:  # las versiones de una cancion ocupan varios vecinos: se pide mas hasta llenar k grupos
            with state["lock"]:  # ef es estado global del indice y debe ser >= kk
                index.set_ef(max(state["ef"], kk))
                ids, dist = index.knn_query(q, k=kk)
            cards: dict[str, list] = {}  # group_id -> [(score, fila)] en orden de score
            for d, i in zip(dist[0], ids[0]):
                cards.setdefault(group[i], []).append((float(1 - d), int(i)))
            if len(cards) >= k or kk >= n:
                break
            kk = min(kk * 2, n)

        results = []
        for versions in list(cards.values())[:k]:
            (score, i), rest = versions[0], versions[1:]
            r = rows[i]
            results.append({
                "track_id": r["track_id"], "title": r["track_name"], "artist": r["artist_name"],
                "album": r["album_name"], "year": r["release_year"], "genres": r["genres"] or [],
                "popularity": r["track_popularity"], "explicit": r["explicit"], "score": score,
                "other_versions": [{"track_id": rows[j]["track_id"], "album": rows[j]["album_name"],
                                    "year": rows[j]["release_year"], "score": s} for s, j in rest],
            })
        return jsonify(query=query, k=k, results=results)

    return app
