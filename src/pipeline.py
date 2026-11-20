"""Pipeline medallon (SPEC §3): bronce -> plata -> oro.

Uso:  uv run python -m src.pipeline {bronze|silver|gold|all}

Cada capa verifica la anterior (SHA-256 contra su manifiesto), corre su QA y SOLO si todo pasa
escribe `_manifest.json` y agrega su linaje. Los controles fallan con AssertionError.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata as md
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

from src.encoder import DEFAULT_MODEL, PASSAGE_PREFIX
from src.spotify_eda import (RAW_COLUMNS, build_artists, build_typed, explode_genres, finding_masks,
                             findings, read_raw_strings, run_qa)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SLUG = "wardabilal/spotify-global-music-dataset-20092025"
MAIN, SECONDARY = "track_data_final.csv", "spotify_data clean.csv"
TEMPLATE_VERSION = "v1"
HNSW = {"M": 16, "ef_construction": 200, "ef_search": 50, "seed": 100}
RECALL_MIN = 0.95  # umbral propuesto en SPEC §8.1 (POR VERIFICAR)

# Diccionario de datos: "significado <- columnas de origen". Una columna sin entrada aqui rompe la corrida.
CATALOG = {
    "silver.tracks": {
        "track_id": "ID Spotify de la cancion; llave unica <- track_id",
        "track_name": "Titulo; null si venia vacio <- track_name",
        "track_number": "Posicion en el album <- track_number",
        "track_popularity": "Popularidad 0-100 de la cancion, foto de un momento no verificado <- track_popularity",
        "track_duration_ms": "Duracion en ms (0 = placeholder) <- track_duration_ms",
        "explicit": "Contenido explicito <- explicit",
        "artist_name": "Nombre del artista (no hay artist_id; la identidad es el nombre) <- artist_name",
        "artist_popularity": "Atributo del ARTISTA (se repite por cancion), 0-100 <- artist_popularity",
        "artist_followers": "Atributo del ARTISTA (se repite por cancion) <- artist_followers",
        "album_id": "ID Spotify del album <- album_id",
        "album_name": "Nombre del album; null si venia vacio <- album_name",
        "album_total_tracks": "Canciones del album <- album_total_tracks",
        "album_type": "album | single | compilation <- album_type",
        "release_raw": "Fecha del ALBUM tal como llego <- album_release_date",
        "release_precision": "day | month | year segun el largo de la fecha <- album_release_date",
        "release_year": "Anio de la fecha del ALBUM; null si '0000' <- album_release_date",
        "release_date": "Fecha completa del ALBUM; null si no trae dia <- album_release_date",
        "genres": "Generos del ARTISTA como lista; null si no hay <- artist_genres",
        "genre_count": "Numero de generos <- artist_genres",
        "duration_min": "Duracion en minutos <- track_duration_ms",
    },
    "silver.artists": {
        "artist_name": "Nombre del artista <- artist_name",
        "n_tracks": "Canciones del artista en el dataset <- track_id",
        "artist_popularity": "Mediana de popularidad del artista <- artist_popularity",
        "artist_followers": "Maximo de seguidores <- artist_followers",
        "pop_distinct": "Valores distintos de popularidad (control de consistencia) <- artist_popularity",
        "followers_distinct": "Valores distintos de seguidores (control) <- artist_followers",
        "median_track_popularity": "Mediana de popularidad de sus canciones <- track_popularity",
        "n_genres": "Maximo de generos <- genre_count",
    },
    "silver.track_genres": {
        "track_id": "ID de la cancion <- track_id",
        "genre": "Un genero del artista (1 fila por cancion x genero) <- artist_genres",
    },
    "silver.findings": {
        "track_id": "Cancion afectada <- track_id",
        "severidad": "critico | alto | medio | bajo <- spotify_eda.finding_masks",
        "hallazgo": "Descripcion de la rareza; se reporta, no se corrige <- spotify_eda.finding_masks",
    },
    "gold.search_docs": {
        "track_id": "ID de la cancion; mismo orden que silver.tracks <- tracks.track_id",
        "doc_text": "Texto indexado (plantilla SPEC §4, sin el prefijo del modelo) <- tracks.{track_name,artist_name,album_name,album_type,release_year,explicit}, track_genres.genre",
        "template_version": "Version de la plantilla <- pipeline.TEMPLATE_VERSION",
        "text_hash": "SHA-256 de doc_text <- doc_text",
        "track_name": "Para mostrar <- tracks.track_name",
        "artist_name": "Para mostrar <- tracks.artist_name",
        "album_name": "Para mostrar <- tracks.album_name",
        "release_year": "Para mostrar; anio del ALBUM <- tracks.release_year",
        "genres": "Para mostrar; lista vacia si no hay <- track_genres.genre",
        "track_popularity": "Para mostrar <- tracks.track_popularity",
        "explicit": "Para mostrar <- tracks.explicit",
    },
    "gold.embedding_ids": {
        "track_id": "ID de la cancion de la fila i de embeddings.npy <- search_docs.track_id",
        "row": "Fila en embeddings.npy y etiqueta en hnsw.index <- orden de search_docs",
    },
    "gold.version_groups": {
        "track_id": "ID de la cancion <- tracks.track_id",
        "group_id": "Hash de artista+titulo normalizados; versiones de una cancion comparten grupo <- tracks.{artist_name,track_name}",
        "group_size": "Canciones del grupo <- group_id",
    },
}


# ------------------------------------------------------------------------ utilidades
def _sha(path: Path) -> str:
    with open(path, "rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _git() -> tuple[str, bool]:
    run = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()  # noqa: E731
    try:
        return run("rev-parse", "--short", "HEAD"), bool(run("status", "--porcelain"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        # shortcut: sin repo git (zip, `git init` sin commits, git ausente) el manifiesto dice "sin-git"; volver a correr dentro de un clon con commits para trazar el codigo
        return "sin-git", True


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _csv_rows(path: Path) -> int:
    with open(path, encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def _check(qa: list[dict], name: str, ok, detail="") -> None:
    qa.append({"control": name, "ok": bool(ok), "detalle": str(detail)})
    assert ok, f"QA FALLO: {name} ({detail})"


def _out(path: Path, data_dir: Path, rows: int, schema=None) -> dict:
    return {"path": path.relative_to(data_dir).as_posix(), "sha256": _sha(path), "rows": rows,
            "bytes": path.stat().st_size, "schema": schema}


def _schema(df: pl.DataFrame) -> dict:
    return {c: str(t) for c, t in df.schema.items()}


def _inputs(data_dir: Path, layer: str, names: list[str]) -> list[dict]:
    """Entradas desde el manifiesto de la capa anterior; falla si el archivo ya no es el que se certifico."""
    mf = data_dir / layer / "_manifest.json"
    assert mf.exists(), f"falta {mf}: corre primero la capa '{layer}'"
    prev = json.loads(mf.read_text(encoding="utf-8"))
    by_name = {Path(o["path"]).name: o for o in prev["outputs"]}
    ins = []
    for n in names:
        o = by_name[n]
        got = _sha(data_dir / o["path"])
        assert got == o["sha256"], f"{o['path']} cambio desde la corrida {prev['run_id']} (sha {got[:12]} != {o['sha256'][:12]})"
        ins.append({"path": o["path"], "sha256": o["sha256"], "rows": o["rows"], "run_id": prev["run_id"]})
    return ins


def _revoke(layer_dir: Path) -> None:
    """Borra el manifiesto ANTES de sobrescribir las salidas: si el QA falla a mitad, la capa queda sin
    certificar (la siguiente capa, la API e init.sh lo detectan) en vez de con un manifiesto viejo que ya no describe los archivos."""
    (layer_dir / "_manifest.json").unlink(missing_ok=True)


def _finish(data_dir: Path, layer: str, run_id: str, started: datetime, fn: str, params: dict,
            inputs: list[dict], outputs: list[dict], qa: list[dict], libs: list[str],
            tables: dict[str, pl.DataFrame] | None = None, edges: list[list[dict]] | None = None) -> dict:
    """Escribe manifiesto + linaje + diccionario. Se llama solo si el QA paso."""
    assert qa and all(q["ok"] for q in qa), "no se escribe manifiesto: hay controles que fallan"
    for name, df in (tables or {}).items():  # diccionario completo ANTES de certificar nada
        assert set(CATALOG[name]) == set(df.columns), f"{name}: columnas sin documentar en CATALOG {set(df.columns) ^ set(CATALOG[name])}"
    commit, dirty = _git()
    manifest = {
        "layer": layer, "run_id": run_id, "created_utc": started.isoformat(timespec="seconds"),
        "code": {"module": f"src.pipeline.{fn}", "git_commit": commit, "git_dirty": dirty},
        "params": params, "inputs": inputs, "outputs": outputs, "qa": qa,
        "env": {"python": sys.version.split()[0], **{p: md.version(p) for p in libs}},
    }
    (data_dir / layer / "_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    lin = data_dir / "_lineage" / "lineage.jsonl"  # append-only: una arista por salida
    lin.parent.mkdir(parents=True, exist_ok=True)
    with open(lin, "a", encoding="utf-8") as fh:
        for o, ins in zip(outputs, edges or [inputs] * len(outputs)):  # edges: entradas propias de cada salida
            fh.write(json.dumps({
                "output": o["path"], "output_sha256": o["sha256"],
                "inputs": [{"path": i["path"], "sha256": i["sha256"]} for i in ins],
                "transformation": f"src.pipeline.{fn}", "run_id": run_id, "git_commit": commit,
            }, ensure_ascii=False) + "\n")

    if tables:
        cat_path = data_dir / "_catalog" / "data_dictionary.json"  # JSON (YAML valido) para no sumar pyyaml
        cat = json.loads(cat_path.read_text(encoding="utf-8")) if cat_path.exists() else {}
        for name, df in tables.items():
            doc = CATALOG[name]
            cat[name] = {c: {"type": str(df.schema[c]), "nullable": df[c].null_count() > 0,
                             "meaning": doc[c].split(" <- ")[0], "derived_from": doc[c].split(" <- ")[1]}
                         for c in df.columns}
        cat_path.parent.mkdir(parents=True, exist_ok=True)
        cat_path.write_text(json.dumps(cat, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def _run_id() -> tuple[str, datetime]:
    t = _now()
    return f"{t:%Y%m%dT%H%M%SZ}-{_git()[0]}", t


# -------------------------------------------------------------------------- bronce
def bronze(src_dir: Path = DATA / "raw", data_dir: Path = DATA) -> dict:
    """Copia byte a byte, write-once. `src_dir` = descarga de kagglehub ya copiada por el EDA v1."""
    rid, t0 = _run_id()
    out = data_dir / "bronze"
    out.mkdir(parents=True, exist_ok=True)
    mf = out / "_manifest.json"
    prev = {Path(o["path"]).name: o["sha256"] for o in json.loads(mf.read_text(encoding="utf-8"))["outputs"]} if mf.exists() else {}
    qa, inputs, outputs = [], [], []
    for name in (MAIN, SECONDARY):
        src, dst = src_dir / name, out / name
        assert src.exists(), f"falta el origen {src}"
        expected = prev.get(name) or _sha(src)
        # tambien si falta dst: un CSV borrado no abre la puerta a otra version del origen
        assert _sha(src) == expected, (f"el origen {src} cambio respecto a bronce (write-once, no se sobrescribe). "
                                       f"Si es una version nueva a proposito, borra {out} entera y vuelve a correr bronze")
        if dst.exists():
            assert _sha(dst) == expected, f"bronce es write-once: {dst} cambio (no se sobrescribe)"
        else:
            shutil.copyfile(src, dst)
        n = _csv_rows(dst)
        _check(qa, f"{name}: sha256 y bytes iguales al origen", _sha(dst) == _sha(src) and dst.stat().st_size == src.stat().st_size)
        with open(dst, encoding="utf-8", newline="") as fh:
            header = next(csv.reader(fh))
        # el secundario tiene otro esquema (track_duration_min, TRUE/FALSE); no se parsea en plata
        _check(qa, f"{name}: header == esquema esperado", header == RAW_COLUMNS if name == MAIN else "track_id" in header)
        _check(qa, f"{name}: registros > 0", n > 0, n)
        inputs.append({"path": src.relative_to(ROOT).as_posix() if src.is_relative_to(ROOT) else src.as_posix(), "sha256": _sha(src), "rows": n, "run_id": None})
        outputs.append(_out(dst, data_dir, n))
    params = {"slug": SLUG, "kagglehub_dataset_version": "POR VERIFICAR (copiado de data/raw del EDA v1; no se registro la version)",
              "download_utc": "POR VERIFICAR (no registrada); mtime del origen en source_mtime_utc",
              "source_mtime_utc": {n: datetime.fromtimestamp((src_dir / n).stat().st_mtime, timezone.utc).isoformat(timespec="seconds") for n in (MAIN, SECONDARY)}}
    return _finish(data_dir, "bronze", rid, t0, "bronze", params, inputs, outputs, qa, [],
                   edges=[[i] for i in inputs])


# --------------------------------------------------------------------------- plata
def silver(data_dir: Path = DATA) -> dict:
    rid, t0 = _run_id()
    ins = _inputs(data_dir, "bronze", [MAIN])
    src = data_dir / ins[0]["path"]
    raw = read_raw_strings(src)
    tracks = build_typed(raw)
    gl = explode_genres(tracks)
    qa = run_qa(src, raw, tracks, gl).to_dicts()  # los 27 controles del EDA v1; lanza AssertionError si falla

    track_genres = gl.select("track_id", "genre")
    artists = build_artists(tracks)
    find = pl.concat([
        tracks.filter(m).select("track_id").with_columns(pl.lit(sev).alias("severidad"), pl.lit(label).alias("hallazgo"))
        for sev, label, m in finding_masks(tracks)
    ])
    got = dict(find.group_by("hallazgo").len().iter_rows())
    want = {h: f for h, f in findings(tracks).select("hallazgo", "filas").iter_rows() if f}
    _check(qa, "findings.parquet cuenta lo mismo que findings()", got == want)
    _check(qa, "tracks 1:1 con bronce", tracks.height == ins[0]["rows"], f"{tracks.height} vs {ins[0]['rows']}")

    tables = {"silver.tracks": tracks, "silver.artists": artists, "silver.track_genres": track_genres, "silver.findings": find}
    (data_dir / "silver" / "_quality").mkdir(parents=True, exist_ok=True)
    _revoke(data_dir / "silver")
    paths = {"silver.tracks": "tracks.parquet", "silver.artists": "artists.parquet",
             "silver.track_genres": "track_genres.parquet", "silver.findings": "_quality/findings.parquet"}
    outputs = []
    for name, df in tables.items():
        p = data_dir / "silver" / paths[name]
        df.write_parquet(p)
        _check(qa, f"{paths[name]}: se relee con las mismas filas", pl.read_parquet(p).height == df.height)
        outputs.append(_out(p, data_dir, df.height, _schema(df)))
    return _finish(data_dir, "silver", rid, t0, "silver", {"findings_in_silver": "marcados, nunca borrados"},
                   ins, outputs, qa, ["polars"], tables)


# ---------------------------------------------------------------------------- oro
def doc_text(r: dict) -> str:
    """Plantilla SPEC §4: campo nulo => se omite la frase entera; sin imputar nada."""
    sent = lambda label, v: f"{label}: {v}" + ("" if v.endswith(".") else ".")  # noqa: E731  evita ".." si el nombre ya termina en punto
    parts = []
    if r["track_name"]:
        parts.append(sent("Canción", r["track_name"]))
    if r["artist_name"]:
        parts.append(sent("Artista", r["artist_name"]))
    if r["album_name"]:
        parts.append(f"Álbum: {r['album_name']} ({r['album_type']}).")
    if r["release_year"] is not None:
        parts.append(f"Año: {r['release_year']}.")
    if r["genres"]:
        parts.append(sent("Géneros", ", ".join(r["genres"])))
    if r["explicit"]:
        parts.append("Contenido explícito.")
    return " ".join(parts)


def build_docs(tracks: pl.DataFrame, track_genres: pl.DataFrame) -> pl.DataFrame:
    g = track_genres.group_by("track_id", maintain_order=True).agg(pl.col("genre").alias("genres"))
    d = tracks.with_columns(pl.col("album_type").cast(pl.String)).drop("genres").join(g, on="track_id", how="left")
    d = d.with_columns(pl.col("genres").fill_null([]))
    texts = [doc_text(r) for r in d.iter_rows(named=True)]
    return d.select(
        "track_id", pl.Series("doc_text", texts), pl.lit(TEMPLATE_VERSION).alias("template_version"),
        pl.Series("text_hash", [hashlib.sha256(t.encode()).hexdigest() for t in texts]),
        "track_name", "artist_name", "album_name", "release_year", "genres", "track_popularity", "explicit",
    )


def version_groups(tracks: pl.DataFrame) -> pl.DataFrame:
    norm = lambda c: pl.col(c).str.to_lowercase().str.replace_all(r"\s+", " ").str.strip_chars()  # noqa: E731
    # sin artista o titulo no hay con que agrupar: el grupo es la propia cancion
    key = pl.when(pl.col("artist_name").is_null() | pl.col("track_name").is_null()).then("track:" + pl.col("track_id")) \
        .otherwise(norm("artist_name") + "\x1f" + norm("track_name"))
    keys = tracks.select(key.alias("k"))["k"].to_list()
    return tracks.select("track_id").with_columns(
        pl.Series("group_id", [hashlib.sha256(k.encode()).hexdigest()[:16] for k in keys])
    ).with_columns(pl.len().over("group_id").alias("group_size"))


def build_index(vecs: np.ndarray):
    import hnswlib

    idx = hnswlib.Index(space="cosine", dim=vecs.shape[1])
    idx.init_index(max_elements=len(vecs), ef_construction=HNSW["ef_construction"], M=HNSW["M"], random_seed=HNSW["seed"])
    idx.add_items(vecs, np.arange(len(vecs)), num_threads=1)  # un hilo: grafo reproducible
    idx.set_ef(HNSW["ef_search"])
    return idx


def recall_at_k(index, vecs: np.ndarray, k: int = 10, n_queries: int = 200) -> float:
    """Recall del HNSW contra fuerza bruta. Consultas = vectores de canciones elegidos con semilla fija.
    shortcut: no son consultas reales de usuario, usar las del conjunto dorado cuando esten etiquetadas.
    Un acierto = devuelto con score >= el k-esimo exacto (robusto a empates)."""
    q = vecs[np.random.default_rng(0).choice(len(vecs), min(n_queries, len(vecs)), replace=False)]
    kth = np.sort(q @ vecs.T, axis=1)[:, -k][:, None]
    _, dist = index.knn_query(q, k=k)
    return float(((1 - dist) >= kth - 1e-5).mean())


def gold(data_dir: Path = DATA, encoder=None) -> dict:
    """`encoder` = (encode, info) con encode: list[str] -> float32 normalizado e info={name, revision, dim}.
    Por defecto el e5-base real (descarga ~1 GB la primera vez)."""
    import hnswlib

    if encoder is None:
        from src.encoder import load_st
        encoder = load_st(DEFAULT_MODEL)
    encode, info = encoder
    rid, t0 = _run_id()
    ins = _inputs(data_dir, "silver", ["tracks.parquet", "track_genres.parquet"])
    tracks = pl.read_parquet(data_dir / ins[0]["path"])
    docs = build_docs(tracks, pl.read_parquet(data_dir / ins[1]["path"]))
    groups = version_groups(tracks)
    ids = docs.select("track_id").with_row_index("row").select("track_id", pl.col("row").cast(pl.Int64))

    t = time.perf_counter()
    vecs = np.ascontiguousarray(encode([PASSAGE_PREFIX + t for t in docs["doc_text"]]), dtype="float32")
    t_encode = time.perf_counter() - t
    t = time.perf_counter()
    index = build_index(vecs)
    t_build = time.perf_counter() - t

    out = data_dir / "gold"
    out.mkdir(parents=True, exist_ok=True)
    _revoke(out)
    docs.write_parquet(out / "search_docs.parquet")
    ids.write_parquet(out / "embedding_ids.parquet")
    groups.write_parquet(out / "version_groups.parquet")
    np.save(out / "embeddings.npy", vecs)
    index.save_index(str(out / "hnsw.index"))

    # QA leyendo lo escrito en disco
    qa: list[dict] = []
    n = tracks.height
    d, e, v = (pl.read_parquet(out / f"{x}.parquet") for x in ("search_docs", "embedding_ids", "version_groups"))
    m, idx = np.load(out / "embeddings.npy"), hnswlib.Index("cosine", info["dim"])
    idx.load_index(str(out / "hnsw.index"), max_elements=n)
    _check(qa, "search_docs: filas, track_id y orden == tracks", d.height == n and d["track_id"].equals(tracks["track_id"]))
    _check(qa, "embedding_ids.track_id == search_docs.track_id", e["track_id"].equals(d["track_id"]) and e["row"].to_list() == list(range(n)))
    _check(qa, "embeddings: float32 y forma (N, dim)", m.dtype == np.float32 and m.shape == (n, info["dim"]), m.shape)
    _check(qa, "embeddings sin NaN/inf", np.isfinite(m).all())
    dev = float(np.abs(np.linalg.norm(m, axis=1) - 1).max())
    _check(qa, "embeddings normalizados L2 (|norma-1| < 1e-3)", dev < 1e-3, f"max desvio {dev:.2e}")
    _check(qa, "hnsw.index contiene N elementos", idx.get_current_count() == n, idx.get_current_count())
    _check(qa, "doc_text no vacio", (d["doc_text"].str.len_chars() > 0).all())
    regen = build_docs(tracks, pl.read_parquet(data_dir / ins[1]["path"]))
    _check(qa, "text_hash == sha256(doc_text) y el texto se regenera igual",
           d["text_hash"].equals(regen["text_hash"]) and d["doc_text"].equals(regen["doc_text"]))
    _check(qa, "version_groups: track_id == tracks y los grupos suman N",
           v["track_id"].equals(tracks["track_id"]) and v.group_by("group_id").agg(pl.col("group_size").first())["group_size"].sum() == n)
    idx.set_ef(HNSW["ef_search"])
    rec = recall_at_k(idx, m)
    _check(qa, f"recall@10 HNSW vs fuerza bruta >= {RECALL_MIN}", rec >= RECALL_MIN, f"{rec:.4f}")

    params = {"template_version": TEMPLATE_VERSION, "model": info, "prefix_passage": PASSAGE_PREFIX,
              "hnsw": {**HNSW, "metric": "cosine (distancia = 1 - coseno)", "library": f"hnswlib {md.version('hnswlib')}",
                       "threads_build": 1},
              "timings_s": {"encode": round(t_encode, 1), "build_index": round(t_build, 1)},
              "recall_threshold": RECALL_MIN, "recall_queries": "200 vectores de canciones (semilla 0)"}
    outputs = [_out(out / f"{x}.parquet", data_dir, n, _schema(df)) for x, df in
               (("search_docs", d), ("embedding_ids", e), ("version_groups", v))]
    outputs += [_out(out / "embeddings.npy", data_dir, n, {"dtype": "float32", "shape": list(m.shape)}),
                _out(out / "hnsw.index", data_dir, idx.get_current_count())]
    tables = {"gold.search_docs": d, "gold.embedding_ids": e, "gold.version_groups": v}
    return _finish(data_dir, "gold", rid, t0, "gold", params, ins, outputs, qa,
                   ["polars", "numpy", "hnswlib", "sentence-transformers", "torch"], tables)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("layer", choices=["bronze", "silver", "gold", "all"])
    a = ap.parse_args()
    for name, fn in (("bronze", bronze), ("silver", silver), ("gold", gold)):
        if a.layer in (name, "all"):
            m = fn()
            print(f"[{name}] run_id={m['run_id']} QA {len(m['qa'])}/{len(m['qa'])} OK")


if __name__ == "__main__":
    main()
