import csv
import hashlib

import numpy as np
import pytest

from src import pipeline
from src.spotify_eda import RAW_COLUMNS

DIM = 16


def fake_encode(texts):
    """Determinista: mismo texto (sin prefijo e5) => mismo vector unitario."""
    out = []
    for t in texts:
        t = t.removeprefix("passage: ").removeprefix("query: ")
        v = np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:8], 16)).normal(size=DIM)
        out.append(v / np.linalg.norm(v))
    return np.array(out, dtype="float32")


FAKE = (fake_encode, {"name": "fake-encoder", "revision": "0" * 40, "dim": DIM})


def make_raw(src):
    """CSV pequeno con el esquema real: versiones duplicadas, artista vacio, sin genero."""
    src.mkdir(parents=True)
    rows = []
    for i in range(30):
        rows.append([f"t{i:03d}", f"Song {i}", "1", str(i * 3 % 100), str(200000 + i), "True" if i % 4 == 0 else "False",
                     f"Artist {i % 7}", "50.0", "1000.0", "['pop', 'rock']" if i % 3 else "", f"alb{i}",
                     f"Album {i}", f"20{10 + i % 15}-01-01", "10", "album"])
    rows[0][1], rows[0][6] = "Same  Song", "Artist 0"  # t000 y t001: misma cancion en otro album (version)
    rows[1][1], rows[1][6] = "same song", "Artist 0"
    rows[2][6] = rows[2][7] = rows[2][8] = rows[2][9] = ""  # artista vacio como en el dato real
    with open(src / pipeline.MAIN, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(RAW_COLUMNS)
        w.writerows(rows)
    (src / pipeline.SECONDARY).write_text("track_id,track_name\nt000,x\n", encoding="utf-8")


def build(tmp_path, with_gold=True):
    make_raw(tmp_path / "raw")
    data = tmp_path / "data"
    pipeline.bronze(tmp_path / "raw", data)
    pipeline.silver(data)
    if with_gold:
        pipeline.gold(data, FAKE)
    return data


@pytest.fixture(scope="session")
def data(tmp_path_factory):
    pytest.importorskip("hnswlib")  # solo existe en Linux/Docker; ver README de pruebas en api.Dockerfile
    return build(tmp_path_factory.mktemp("medallon"))
