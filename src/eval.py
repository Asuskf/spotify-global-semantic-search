"""Evaluacion (SPEC §8.3): BM25 vs buscador semantico sobre el conjunto dorado.

Uso:  uv run python -m src.eval
Falla si hay consultas sin etiquetar: no se inventan etiquetas ni se afirma que uno gane.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl

from src.encoder import QUERY_PREFIX

GOLD = Path(__file__).resolve().parents[1] / "data" / "gold"
K = 10


def tokens(text: str) -> list[str]:
    """Minusculas y sin tildes, para que 'canción' y 'cancion' coincidan."""
    t = unicodedata.normalize("NFKD", text.lower())
    return re.findall(r"\w+", "".join(c for c in t if not unicodedata.combining(c)))


def bm25_index(docs: list[str]):
    counts = [Counter(tokens(d)) for d in docs]
    df = Counter(t for c in counts for t in c)
    return counts, [sum(c.values()) for c in counts], df


def bm25_rank(index, query: str, k: int = K, k1: float = 1.5, b: float = 0.75) -> list[int]:
    """Filas de los k mejores documentos con score > 0 (BM25 clasico, idf de Lucene)."""
    counts, lens, df = index
    n, avg = len(counts), sum(lens) / len(counts)
    score = np.zeros(n)
    for t in set(tokens(query)) & df.keys():
        idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
        for i, c in enumerate(counts):
            if f := c.get(t):
                score[i] += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * lens[i] / avg))
    return [int(i) for i in np.argsort(-score, kind="stable")[:k] if score[i] > 0]


def recall_at_k(ranked: list[str], relevant: set[str], k: int = K) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant)


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int = K) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, t in enumerate(ranked[:k]) if t in relevant)
    return dcg / sum(1 / math.log2(i + 2) for i in range(min(len(relevant), k)))


def load_golden(path: Path) -> list[dict]:
    queries = json.loads(path.read_text(encoding="utf-8"))["queries"]
    unlabeled = [q["id"] for q in queries if not q["relevant_track_ids"]]
    assert not unlabeled, (f"{len(unlabeled)} de {len(queries)} consultas sin etiquetar ({', '.join(unlabeled[:5])}...). "
                           f"Rellena relevant_track_ids en {path} (quien etiqueta: POR DEFINIR); no se evalua con etiquetas inventadas.")
    return queries


def main(gold: Path = GOLD) -> None:
    import hnswlib

    from src.encoder import load_st

    queries = load_golden(gold / "eval" / "golden_queries.json")
    docs = pl.read_parquet(gold / "search_docs.parquet")
    ids, bm25 = docs["track_id"].to_list(), bm25_index(docs["doc_text"].to_list())
    params = json.loads((gold / "_manifest.json").read_text(encoding="utf-8"))["params"]
    info = params["model"]
    encode, _ = load_st(info["name"])
    index = hnswlib.Index("cosine", info["dim"])
    index.load_index(str(gold / "hnsw.index"), max_elements=docs.height)
    index.set_ef(params["hnsw"]["ef_search"])
    rows = []
    for q in queries:
        rel = set(q["relevant_track_ids"])
        hits, _ = index.knn_query(np.asarray(encode([QUERY_PREFIX + q["text"]]), dtype="float32"), k=K)
        for name, ranked in (("bm25", [ids[i] for i in bm25_rank(bm25, q["text"])]),
                             ("semantico", [ids[i] for i in hits[0]])):
            rows.append({"id": q["id"], "lang": q["lang"], "type": q["type"], "metodo": name,
                         "recall@10": recall_at_k(ranked, rel), "ndcg@10": ndcg_at_k(ranked, rel)})
    res = pl.DataFrame(rows)
    out = GOLD.parents[1] / "artifacts" / "tables" / "golden_eval.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    res.write_csv(out)
    print(res.group_by("metodo").agg(pl.col("recall@10").mean(), pl.col("ndcg@10").mean(), pl.len().alias("consultas")))
    print(f"detalle por consulta: {out}")


if __name__ == "__main__":
    main()
