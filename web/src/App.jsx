import { useEffect, useState } from "react";
import { dash, formatScore, formatGenres } from "./format.js";

const MAX_QUERY = 300;
const EJEMPLOS = [
  "rap melancólico de los 2010",
  "chill acoustic songs for studying",
  "canciones tristes para llorar",
  "upbeat 80s pop for a road trip",
];

// Cada dato lleva su etiqueta visible (dt) y el valor solo en el elemento con testid.
function Dato({ label, id, children }) {
  return (
    <div className="dato">
      <dt>{label}</dt>
      <dd data-testid={id}>{children}</dd>
    </div>
  );
}

function Card({ r }) {
  return (
    <li className="card" data-testid="result-card">
      <div className="card-head">
        <div className="card-title">
          <h3 data-testid="result-title">{dash(r.title)}</h3>
          <p className="artist" data-testid="result-artist">{dash(r.artist)}</p>
        </div>
        <p className="score">
          <span className="score-label">Similitud</span>
          <span className="score-value" data-testid="result-score" title="Similitud coseno">{formatScore(r.score)}</span>
        </p>
      </div>
      <dl className="datos">
        <Dato label="Álbum" id="result-album">{dash(r.album)}</Dato>
        <Dato label="Año" id="result-year">{dash(r.year)}</Dato>
        <Dato label="Popularidad" id="result-popularity">{dash(r.popularity)}</Dato>
      </dl>
      <p className="genres" data-testid="result-genres">{formatGenres(r.genres)}</p>
      {r.explicit && <span className="badge" data-testid="result-explicit">Explícito</span>}
      {r.other_versions?.length > 0 && <Versions list={r.other_versions} />}
    </li>
  );
}

// Botón con aria-expanded en lugar de <details>: el testid vive en un solo botón y el estado es explícito.
function Versions({ list }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="versions">
      <button type="button" className="toggle" aria-expanded={open} data-testid="other-versions-toggle"
        onClick={() => setOpen(!open)}>
        Otras versiones ({list.length})
        <svg className="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
      </button>
      {open && (
        <ul data-testid="other-versions-list">
          {list.map((v) => (
            <li key={v.track_id}>
              {dash(v.album)} · {dash(v.year)} · similitud {formatScore(v.score)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState({ status: "idle" }); // idle | loading | ok | error
  const [health, setHealth] = useState(null);

  // El estado del servicio es informativo: si falla, la búsqueda sigue funcionando.
  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setHealth)
      .catch(() => setHealth(false));
  }, []);

  async function search(q) {
    q = q.trim();
    if (!q) return setState({ status: "error", message: "Escribe una consulta." });
    setState({ status: "loading" });
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, k: 10 }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || `Error ${res.status} del servidor.`);
      setState({ status: "ok", results: body.results });
    } catch (e) {
      const network = e instanceof TypeError;
      setState({ status: "error", message: network ? "No se pudo conectar con el servidor." : e.message });
    }
  }

  const pick = (q) => {
    setQuery(q);
    search(q);
  };

  const loading = state.status === "loading";
  const healthOk = !!health;

  return (
    <>
      <header className="top">
        <div className="wrap top-in">
          <div className="lockup">
            <span className="lockup-name">SEVEN TECH</span>
            <span className="lockup-sub">Python Guaranda</span>
          </div>
        </div>
      </header>

      <main className="wrap">
        <section className="hero">
          <h1>Encuentra la canción que tienes en la cabeza</h1>
          <p className="sub">Cuéntanos en tus palabras cómo suena y te mostramos las más parecidas.</p>
          <span className="rule" aria-hidden="true" />

          <form className="finder" onSubmit={(e) => { e.preventDefault(); search(query); }}>
            <label htmlFor="q">Describe la canción</label>
            <div className="row">
              <input
                id="q"
                data-testid="search-input"
                value={query}
                maxLength={MAX_QUERY}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="p. ej. rap melancólico de los 2010"
              />
              <button type="submit" className="go" data-testid="search-button" disabled={loading}>
                Buscar
              </button>
            </div>
          </form>

          <div className="examples">
            <span id="ej-label">Prueba con:</span>
            <ul aria-labelledby="ej-label">
              {EJEMPLOS.map((q) => (
                <li key={q}>
                  {/* deshabilitado al cargar, como "Buscar": una respuesta vieja no pisa a la nueva */}
                  <button type="button" className="chip" data-testid="example-query" disabled={loading} onClick={() => pick(q)}>{q}</button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <div className="status" aria-live="polite">
          {loading && <p className="msg" data-testid="state-loading"><span className="spin" aria-hidden="true" />Buscando…</p>}
          {state.status === "error" && <p className="msg error" role="alert" data-testid="state-error">{state.message}</p>}
          {state.status === "ok" && state.results.length === 0 && (
            <p className="msg" data-testid="state-empty">Sin resultados para esta consulta. Prueba con otras palabras.</p>
          )}
        </div>

        {state.status === "ok" && state.results.length > 0 && (
          <ol className="results" data-testid="results-list">
            {state.results.map((r) => <Card key={r.track_id} r={r} />)}
          </ol>
        )}
      </main>

      <footer className="wrap foot">
        <p data-testid="health-status" role="status">
          <span className={`dot ${healthOk ? "on" : ""}`} aria-hidden="true" />
          {healthOk
            ? `Servicio activo · ${health.n_vectors} canciones indexadas · modelo ${health.model}`
            : health === false ? "Estado del servicio no disponible" : "Comprobando servicio…"}
        </p>
      </footer>
    </>
  );
}
