"""Codificador de texto real (sentence-transformers). Pipeline, API y eval lo reciben como
funcion inyectable `list[str] -> ndarray float32 normalizado`, asi las pruebas usan uno falso."""
from __future__ import annotations

from pathlib import Path

DEFAULT_MODEL = "intfloat/multilingual-e5-base"
PASSAGE_PREFIX = "passage: "  # convencion e5; POR VERIFICAR contra la ficha del modelo
QUERY_PREFIX = "query: "


def load_st(name: str = DEFAULT_MODEL):
    """Devuelve (encode, info). Descarga el modelo la primera vez (~1 GB para e5-base)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(name, device="cpu")
    # commit exacto de HuggingFace = nombre de la carpeta snapshots/<commit> del cache (config._commit_hash sale vacio)
    from huggingface_hub import snapshot_download

    revision = Path(snapshot_download(name, local_files_only=True)).name  # solo lee el cache (sin local_files_only baja todos los formatos del repo)
    assert revision, f"no pude leer la revision (commit HF) de {name}"
    info = {"name": name, "revision": revision, "dim": model.get_embedding_dimension()}

    def encode(texts: list[str]):
        return model.encode(texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True,
                            show_progress_bar=len(texts) > 100).astype("float32")

    return encode, info
