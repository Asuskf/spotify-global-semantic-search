import json

import polars as pl
import pytest

from src import pipeline
from tests.conftest import FAKE, build, make_raw


def test_bronce_falla_si_cambia_el_hash(tmp_path):
    make_raw(tmp_path / "raw")
    data = tmp_path / "data"
    pipeline.bronze(tmp_path / "raw", data)
    pipeline.bronze(tmp_path / "raw", data)  # misma entrada: pasa
    with open(data / "bronze" / pipeline.MAIN, "ab") as fh:
        fh.write(b"x")
    with pytest.raises(AssertionError, match="write-once"):
        pipeline.bronze(tmp_path / "raw", data)


def test_bronce_falla_si_se_borra_el_csv_y_cambia_el_origen(tmp_path):
    make_raw(tmp_path / "raw")
    data = tmp_path / "data"
    pipeline.bronze(tmp_path / "raw", data)
    (data / "bronze" / pipeline.MAIN).unlink()
    with open(tmp_path / "raw" / pipeline.MAIN, "ab") as fh:  # "nueva version" del dataset
        fh.write(b"x")
    with pytest.raises(AssertionError, match="write-once"):
        pipeline.bronze(tmp_path / "raw", data)


def test_plata_revoca_su_manifiesto_si_falla_a_mitad(tmp_path, monkeypatch):
    d = build(tmp_path, with_gold=False)  # plata previa valida
    real, calls = pl.DataFrame.write_parquet, []

    def falla_en_la_segunda(self, *a, **kw):
        calls.append(1)
        if len(calls) == 2:
            raise OSError("disco lleno (simulado)")
        return real(self, *a, **kw)

    monkeypatch.setattr(pl.DataFrame, "write_parquet", falla_en_la_segunda)
    with pytest.raises(OSError, match="simulado"):
        pipeline.silver(d)
    assert not (d / "silver" / "_manifest.json").exists()  # tracks.parquet ya cambio: nada lo certifica


def test_columna_sin_documentar_no_certifica_la_capa(tmp_path, monkeypatch):
    make_raw(tmp_path / "raw")
    data = tmp_path / "data"
    pipeline.bronze(tmp_path / "raw", data)
    incompleto = {k: v for k, v in pipeline.CATALOG["silver.tracks"].items() if k != "duration_min"}
    monkeypatch.setitem(pipeline.CATALOG, "silver.tracks", incompleto)
    with pytest.raises(AssertionError, match="sin documentar"):
        pipeline.silver(data)
    assert not (data / "silver" / "_manifest.json").exists()
    lin = (data / "_lineage" / "lineage.jsonl").read_text(encoding="utf-8")
    assert '"output": "silver/' not in lin


def test_oro_con_encoder_falso_pasa_qa_y_escribe_manifiesto_y_linaje(data):
    m = json.loads((data / "gold" / "_manifest.json").read_text(encoding="utf-8"))
    assert m["layer"] == "gold" and all(q["ok"] for q in m["qa"])
    assert any("recall@10" in q["control"] for q in m["qa"])
    assert m["params"]["model"]["name"] == "fake-encoder"
    assert {o["path"] for o in m["outputs"]} >= {"gold/hnsw.index", "gold/embeddings.npy", "gold/search_docs.parquet"}
    assert m["inputs"][0]["run_id"] == json.loads((data / "silver" / "_manifest.json").read_text(encoding="utf-8"))["run_id"]
    lin = [json.loads(x) for x in (data / "_lineage" / "lineage.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {x["output"].split("/")[0] for x in lin} == {"bronze", "silver", "gold"}
    vec = next(x for x in lin if x["output"] == "gold/embeddings.npy")
    assert vec["inputs"][0]["path"] == "silver/tracks.parquet"
    assert "gold.search_docs" in json.loads((data / "_catalog" / "data_dictionary.json").read_text(encoding="utf-8"))


def test_oro_no_escribe_manifiesto_si_el_qa_falla(tmp_path):
    pytest.importorskip("hnswlib")
    d = build(tmp_path, with_gold=True)  # con un oro previo valido: su manifiesto tampoco debe sobrevivir
    sin_normalizar = (lambda t: FAKE[0](t) * 2, FAKE[1])
    with pytest.raises(AssertionError, match="normalizados"):
        pipeline.gold(d, sin_normalizar)
    assert not (d / "gold" / "_manifest.json").exists()  # los archivos ya se sobrescribieron: nada los certifica


def test_plantilla_omite_campos_nulos():
    base = dict(track_name="A", artist_name=None, album_name=None, album_type="single", release_year=None,
                genres=[], explicit=False)
    assert pipeline.doc_text(base) == "Canción: A."
    full = dict(base, artist_name="B", album_name="C", release_year=2020, genres=["pop", "rock"], explicit=True)
    assert pipeline.doc_text(dict(full, artist_name="BUNT.")).count("..") == 0
    assert pipeline.doc_text(full) == "Canción: A. Artista: B. Álbum: C (single). Año: 2020. Géneros: pop, rock. Contenido explícito."


def test_versiones_comparten_grupo(data):
    v = pl.read_parquet(data / "gold" / "version_groups.parquet")
    g = v.filter(pl.col("track_id").is_in(["t000", "t001"]))
    assert g["group_id"].n_unique() == 1 and g["group_size"].to_list() == [2, 2]
    assert v.filter(pl.col("track_id") == "t002")["group_size"].item() == 1  # sin artista: no se agrupa


def test_git_ausente_se_registra_como_sin_git(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)  # carpeta sin repo git: zip, o `git init` sin commits
    assert pipeline._git() == ("sin-git", True)
