import pytest

from src import eval as ev


def test_bm25_ordena_por_coincidencia_y_ignora_tildes():
    docs = ["Canción: Luna. Géneros: pop.", "Canción: Sol. Géneros: rock.", "Canción: Mar. Géneros: rock, pop."]
    idx = ev.bm25_index(docs)
    assert ev.bm25_rank(idx, "cancion rock", k=3)[0] == 1  # doc corto con 'rock' antes que el largo
    assert ev.bm25_rank(idx, "jazz") == []


def test_metricas():
    assert ev.recall_at_k(["a", "x", "b"], {"a", "b", "c"}) == pytest.approx(2 / 3)
    assert ev.ndcg_at_k(["a", "b"], {"a", "b"}) == pytest.approx(1.0)
    assert ev.ndcg_at_k(["x", "a"], {"a"}) == pytest.approx(1 / 1.5849625, rel=1e-5)


def test_falla_si_hay_consultas_sin_etiquetar():
    with pytest.raises(AssertionError, match="sin etiquetar"):
        ev.load_golden(ev.GOLD / "eval" / "golden_queries.json")
