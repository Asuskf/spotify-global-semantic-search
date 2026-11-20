"""EDA del Spotify Global Music Dataset (2009-2025): carga, tipado, QA y graficos.

Principio: los datos que entran son los que salen. Todo paso que transforma datos
tiene un control que FALLA RUIDOSAMENTE (AssertionError) si algo no cuadra.
"""
from __future__ import annotations

import ast
import csv
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]

RAW_COLUMNS = [
    "track_id", "track_name", "track_number", "track_popularity", "track_duration_ms",
    "explicit", "artist_name", "artist_popularity", "artist_followers", "artist_genres",
    "album_id", "album_name", "album_release_date", "album_total_tracks", "album_type",
]


@dataclass(frozen=True)
class Config:
    slug: str = "wardabilal/spotify-global-music-dataset-20092025"
    main_file: str = "track_data_final.csv"
    secondary_file: str = "spotify_data clean.csv"
    raw_dir: Path = ROOT / "data" / "raw"
    processed_dir: Path = ROOT / "data" / "processed"
    figures_dir: Path = ROOT / "artifacts" / "figures"
    tables_dir: Path = ROOT / "artifacts" / "tables"
    top_n: int = 15
    min_genre_tracks: int = 30  # minimo de canciones para comparar un genero
    release_window: tuple[int, int] = (2009, 2025)  # ventana que declara el dataset
    colors: dict = field(default_factory=lambda: {
        "blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "grey": "#8a8985",
        "ink": "#0b0b0b", "ink2": "#52514e", "surface": "#fcfcfb",
    })


# --------------------------------------------------------------------------- carga
def download_raw(cfg: Config) -> Path:
    """Descarga con kagglehub y deja una copia en data/raw (reproducible, sin Kaggle despues)."""
    import kagglehub

    src = Path(kagglehub.dataset_download(cfg.slug))
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    for name in (cfg.main_file, cfg.secondary_file):
        shutil.copy2(src / name, cfg.raw_dir / name)
    return cfg.raw_dir


def read_raw_strings(path: Path) -> pl.DataFrame:
    """Lee el CSV como TEXTO puro con el modulo csv (tolera comillas sin escapar, p. ej.
    `The 12" Singles`, que rompen el parser de Polars). Nada se interpreta aqui."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    bad = [i for i, r in enumerate(body, start=2) if len(r) != len(header)]
    assert not bad, f"{path.name}: filas con numero de campos distinto al header: {bad[:5]}"
    return pl.DataFrame(body, schema=header, orient="row")


# ------------------------------------------------------------------------- tipado
def build_typed(raw: pl.DataFrame) -> pl.DataFrame:
    """Esquema explicito. Vacio -> null (nunca se inventa un valor)."""
    assert raw.columns == RAW_COLUMNS, f"columnas inesperadas: {raw.columns}"
    nn = lambda c: pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c))  # noqa: E731
    d = pl.col("album_release_date")
    typed = raw.select(
        pl.col("track_id"),
        nn("track_name").alias("track_name"),
        pl.col("track_number").cast(pl.Int32),
        pl.col("track_popularity").cast(pl.Int32),
        pl.col("track_duration_ms").cast(pl.Int64),
        (pl.col("explicit") == "True").alias("explicit"),
        nn("artist_name").alias("artist_name"),
        nn("artist_popularity").cast(pl.Float64).cast(pl.Int32).alias("artist_popularity"),
        nn("artist_followers").cast(pl.Float64).cast(pl.Int64).alias("artist_followers"),
        pl.col("album_id"),
        nn("album_name").alias("album_name"),
        pl.col("album_total_tracks").cast(pl.Int32),
        pl.col("album_type").cast(pl.Enum(["album", "single", "compilation"])),
        pl.col("album_release_date").alias("release_raw"),
        pl.when(d.str.len_chars() == 10).then(pl.lit("day"))
        .when(d.str.len_chars() == 7).then(pl.lit("month"))
        .when(d.str.len_chars() == 4).then(pl.lit("year")).alias("release_precision"),
        # '0000' no es un anio real: queda null y se reporta como hallazgo
        pl.when(d.str.slice(0, 4) == "0000").then(None)
        .otherwise(d.str.slice(0, 4).cast(pl.Int32)).alias("release_year"),
        pl.when(d.str.len_chars() == 10).then(d.str.to_date("%Y-%m-%d", strict=True))
        .otherwise(None).alias("release_date"),
        pl.col("artist_genres").map_elements(
            lambda s: ast.literal_eval(s) if s else None, return_dtype=pl.List(pl.String)
        ).alias("genres"),
    )
    return typed.with_columns(
        pl.col("genres").list.len().alias("genre_count"),
        (pl.col("track_duration_ms") / 60000).alias("duration_min"),
    )


def explode_genres(typed: pl.DataFrame) -> pl.DataFrame:
    """Tabla larga track x genero (solo canciones con al menos un genero)."""
    return (
        typed.filter(pl.col("genre_count") > 0)
        .select("track_id", "artist_name", "track_popularity", "genres")
        .explode("genres").rename({"genres": "genre"})
    )


# ----------------------------------------------------------------------------- QA
def _same(a: pl.Series, b: pl.Series) -> int:
    """Numero de filas distintas tratando null == null."""
    return int((~a.eq_missing(b)).sum())


def run_qa(path: Path, raw: pl.DataFrame, typed: pl.DataFrame, genre_long: pl.DataFrame) -> pl.DataFrame:
    """Lo que entra es lo que sale. Devuelve la tabla de controles; lanza AssertionError si alguno falla."""
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    # 1) conteo independiente de registros en el archivo
    with open(path, encoding="utf-8", newline="") as fh:
        n_file = sum(1 for _ in csv.reader(fh)) - 1
    add("filas archivo == filas crudas", n_file == raw.height, f"{n_file} vs {raw.height}")
    add("filas crudas == filas tipadas", raw.height == typed.height, f"{raw.height} vs {typed.height}")

    # 2) identidad y orden de las llaves
    add("track_id unico", typed["track_id"].n_unique() == typed.height, f"{typed['track_id'].n_unique()} unicos")
    add("track_id identico y en el mismo orden", raw["track_id"].equals(typed["track_id"]), "")

    # 3) ida y vuelta por columna: tipado -> texto original
    def rt(col: str, back: pl.Series) -> None:
        bad = _same(raw[col], back)
        add(f"ida y vuelta: {col}", bad == 0, f"{bad} filas distintas")

    for c in ("track_name", "artist_name", "album_name"):
        rt(c, typed[c].fill_null(""))
    for c in ("track_number", "track_popularity", "track_duration_ms", "album_total_tracks"):
        rt(c, typed[c].cast(pl.String))
    rt("explicit", pl.Series(["True" if v else "False" for v in typed["explicit"]]))
    for c in ("artist_popularity", "artist_followers"):  # el crudo trae "80.0"
        orig = raw[c].replace("", None).cast(pl.Float64)
        bad = _same(orig, typed[c].cast(pl.Float64))
        add(f"ida y vuelta: {c}", bad == 0, f"{bad} filas distintas")
    rt("album_id", typed["album_id"])
    rt("album_type", typed["album_type"].cast(pl.String))
    rt("album_release_date", typed["release_raw"])
    add("album_release_date: precision cubre todas las filas", typed["release_precision"].null_count() == 0, "")
    rt("artist_genres", pl.Series([repr(g) if g is not None else "" for g in typed["genres"].to_list()]))

    # 4) rangos imposibles (fallan; los casos raros pero posibles van a hallazgos)
    add("popularidad cancion en [0,100]", typed["track_popularity"].is_between(0, 100).all(), "")
    add("popularidad artista en [0,100]", typed["artist_popularity"].drop_nulls().is_between(0, 100).all(), "")
    add("duracion >= 0", (typed["track_duration_ms"] >= 0).all(), "")
    add("seguidores >= 0", (typed["artist_followers"].drop_nulls() >= 0).all(), "")
    add("track_number >= 1", (typed["track_number"] >= 1).all(), "")

    # 5) tabla larga de generos conserva todo
    add("sum(genre_count) == filas tabla larga", int(typed["genre_count"].sum()) == genre_long.height,
        f"{int(typed['genre_count'].sum())} vs {genre_long.height}")
    back = (genre_long.group_by("track_id", maintain_order=True).agg(pl.col("genre")))
    ref = typed.filter(pl.col("genre_count") > 0).select("track_id", "genres")
    add("regrupar generos == lista original", back["genre"].equals(ref["genres"]) and back["track_id"].equals(ref["track_id"]), "")
    add("canciones con genero + sin genero == total",
        genre_long["track_id"].n_unique() + int((typed["genre_count"].fill_null(0) == 0).sum()) == typed.height, "")

    out = pl.DataFrame(checks, schema=["control", "ok", "detalle"], orient="row")
    failed = out.filter(~pl.col("ok"))
    assert failed.is_empty(), f"QA FALLO:\n{failed}"
    return out


def assert_partition(table: pl.DataFrame, count_col: str, total: int, label: str) -> None:
    """Una tabla agregada que alimenta un grafico debe sumar exactamente el total de origen."""
    got = int(table[count_col].sum())
    assert got == total, f"[QA grafico] {label}: suma {got} != total origen {total}"


# ------------------------------------------------------------------------ hallazgos
def finding_masks(typed: pl.DataFrame) -> list[tuple[str, str, pl.Series]]:
    """(severidad, hallazgo, mascara por fila). Una sola definicion para el conteo y para auditar por track_id."""
    lo, hi = Config().release_window
    rows = [
        ("critico", "artista vacio (sin popularidad/seguidores/generos)", typed["artist_name"].is_null()),
        ("alto", "sin ningun genero (lista vacia o artista vacio)", typed["genre_count"].fill_null(0) == 0),
        ("alto", f"lanzamiento fuera de {lo}-{hi}", (typed["release_year"] < lo) | (typed["release_year"] > hi)),
        ("medio", "fecha de lanzamiento '0000' (anio invalido)", typed["release_year"].is_null()),
        ("medio", "fecha solo con anio o anio-mes (sin dia)", typed["release_precision"] != "day"),
        ("medio", "nombre de cancion o album vacio", typed["track_name"].is_null() | typed["album_name"].is_null()),
        ("medio", "track_number > album_total_tracks", typed["track_number"] > typed["album_total_tracks"]),
        ("medio", "duracion = 0 ms (placeholder; se excluye de T3)", typed["track_duration_ms"] == 0),
        ("bajo", "popularidad de cancion = 0", typed["track_popularity"] == 0),
        ("bajo", "mismo artista + mismo nombre de cancion (posible duplicado)",
         typed.select(pl.struct("artist_name", "track_name").is_duplicated()).to_series()),
        ("bajo", "nombre de cancion solo numerico", typed["track_name"].str.contains(r"^\d+$")),
    ]
    return [(sev, label, m.fill_null(False)) for sev, label, m in rows]


def findings(typed: pl.DataFrame) -> pl.DataFrame:
    """Rarezas reales del dato (no son error de carga). Se reportan, no se corrigen en silencio."""
    rows = [(sev, label, int(m.sum())) for sev, label, m in finding_masks(typed)]
    return pl.DataFrame(rows, schema=["severidad", "hallazgo", "filas"], orient="row").with_columns(
        (pl.col("filas") / typed.height * 100).round(2).alias("pct")
    )


# ---------------------------------------------------------------------- artistas
def build_artists(typed: pl.DataFrame) -> pl.DataFrame:
    """Una fila por artista (el CSV no trae artist_id: la identidad es el NOMBRE, homonimos POR VERIFICAR).
    Los atributos de artista se repiten por cancion: promediar por cancion sobre-pondera a los prolificos."""
    return (
        typed.filter(pl.col("artist_name").is_not_null())
        .group_by("artist_name")
        .agg(
            pl.len().alias("n_tracks"),
            pl.col("artist_popularity").median().alias("artist_popularity"),
            pl.col("artist_followers").max().alias("artist_followers"),
            pl.col("artist_popularity").n_unique().alias("pop_distinct"),
            pl.col("artist_followers").n_unique().alias("followers_distinct"),
            pl.col("track_popularity").median().alias("median_track_popularity"),
            pl.col("genre_count").max().alias("n_genres"),
        )
    )


# ----------------------------------------------------------------------- graficos
def apply_style(cfg: Config) -> None:
    import matplotlib as mpl

    c = cfg.colors
    mpl.rcParams.update({
        "figure.facecolor": c["surface"], "axes.facecolor": c["surface"], "savefig.facecolor": c["surface"],
        "axes.edgecolor": "#c9c8c3", "axes.labelcolor": c["ink2"], "text.color": c["ink"],
        "xtick.color": c["ink2"], "ytick.color": c["ink2"], "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.8,
        "axes.axisbelow": True, "axes.titlelocation": "left", "axes.titleweight": "bold",
        "axes.titlesize": 12, "font.size": 10, "figure.dpi": 110, "savefig.dpi": 160,
        "axes.prop_cycle": mpl.cycler(color=[c["blue"], c["orange"], c["aqua"]]),
    })


def save_fig(fig, name: str, cfg: Config) -> Path:
    cfg.figures_dir.mkdir(parents=True, exist_ok=True)
    out = cfg.figures_dir / f"{name}.png"
    fig.savefig(out, bbox_inches="tight")
    assert out.stat().st_size > 5_000, f"figura vacia: {out}"
    return out
