import shutil

import polars as pl
import pytest

from src.api.app import create_app
from tests.conftest import fake_encode


@pytest.fixture(scope="module")
def client(data):
    return create_app(data / "gold", fake_encode).test_client()


def doc(data, i):
    return pl.read_parquet(data / "gold" / "search_docs.parquet")["doc_text"][i]


def post(client, **body):
    return client.post("/search", json=body)


def test_health(client):
    r = client.get("/health")
    j = r.get_json()
    assert r.status_code == 200
    assert j["status"] == "ok" and j["n_vectors"] == 30 and j["model"] == "fake-encoder" and j["gold_run_id"]


def test_search_valido_encuentra_la_cancion_exacta(client, data):
    r = post(client, query=doc(data, 5), k=5)
    j = r.get_json()
    assert r.status_code == 200 and j["k"] == 5 and len(j["results"]) == 5
    top = j["results"][0]
    assert top["track_id"] == "t005" and top["score"] == pytest.approx(1.0, abs=1e-5)
    assert set(top) == {"track_id", "title", "artist", "album", "year", "genres", "popularity", "explicit", "score", "other_versions"}
    scores = [x["score"] for x in j["results"]]
    assert scores == sorted(scores, reverse=True)


def test_k_por_defecto_es_10(client):
    assert post(client, query="rock").get_json()["k"] == 10


def test_versiones_se_colapsan_en_una_tarjeta(client, data):
    j = post(client, query=doc(data, 0), k=30).get_json()
    ids = [x["track_id"] for x in j["results"]]
    assert len(ids) == 29  # 30 canciones, 2 son versiones de lo mismo; los k grupos se llenan pidiendo mas vecinos
    card = next(x for x in j["results"] if x["track_id"] in ("t000", "t001"))
    other = {"t000", "t001"} - {card["track_id"]}
    assert [o["track_id"] for o in card["other_versions"]] == list(other)
    assert not other & set(ids)


def test_artista_nulo_y_sin_genero(client, data):
    top = post(client, query=doc(data, 2), k=1).get_json()["results"][0]
    assert top["track_id"] == "t002" and top["artist"] is None and top["genres"] == []


@pytest.mark.parametrize("body", [
    {"query": ""}, {"query": "   "}, {"k": 3}, {"query": 5}, {"query": "x" * 301},
    {"query": "rock", "k": 0}, {"query": "rock", "k": 51}, {"query": "rock", "k": "3"}, {"query": "rock", "k": True},
])
def test_entradas_invalidas_dan_400(client, body):
    r = client.post("/search", json=body)
    assert r.status_code == 400 and r.get_json()["error"]


def test_json_invalido_da_400(client):
    r = client.post("/search", data="{no es json", content_type="application/json")
    assert r.status_code == 400 and "JSON" in r.get_json()["error"]


def test_sin_indice_da_503(tmp_path):
    c = create_app(tmp_path, fake_encode).test_client()
    assert post(c, query="rock").status_code == 503
    assert c.get("/health").status_code == 503


def test_oro_sin_manifiesto_da_503(data, tmp_path):
    """Archivos de oro presentes pero sin certificar (QA fallido): no se sirven."""
    gold = shutil.copytree(data / "gold", tmp_path / "gold")
    (gold / "_manifest.json").unlink()
    assert create_app(gold, fake_encode).test_client().get("/health").status_code == 503


def test_oro_certificado_sin_indice_falla_con_la_ruta(data, tmp_path):
    gold = shutil.copytree(data / "gold", tmp_path / "gold")
    (gold / "hnsw.index").unlink()
    with pytest.raises(AssertionError, match=r"faltan \['hnsw.index'\]"):
        create_app(gold, fake_encode)
