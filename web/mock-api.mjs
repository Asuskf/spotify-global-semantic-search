// SOLO DESARROLLO: API falsa con datos inventados para ver la UI sin backend.
// Consultas especiales: "vacio" -> 0 resultados, "error" -> 503. Puerto 5000.
import http from "node:http";

const fake = (i) => ({
  track_id: `FALSO-${i}`,
  title: `Canción de prueba ${i}`,
  artist: i % 3 === 0 ? null : `Artista falso ${i}`,
  album: i % 4 === 0 ? null : `Álbum falso ${i}`,
  year: i % 4 === 0 ? null : 2000 + i,
  genres: i % 2 ? [] : ["género falso", "otro género"],
  popularity: 40 + i,
  explicit: i % 2 === 0,
  score: 0.9 - i * 0.05,
  other_versions: i === 1 ? [{ track_id: "FALSO-1b", album: "Deluxe falso", year: 2020, score: 0.85 }] : [],
});

const send = (res, code, obj) => {
  res.writeHead(code, { "Content-Type": "application/json" });
  res.end(JSON.stringify(obj));
};

http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/health")
    return send(res, 200, { status: "ok", model: "modelo-falso", n_vectors: 0, gold_run_id: "mock" });
  if (req.method === "POST" && req.url === "/search") {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      const { query = "", k = 10 } = JSON.parse(raw || "{}");
      if (!query.trim()) return send(res, 400, { error: "La consulta no puede estar vacía." });
      if (query === "error") return send(res, 503, { error: "El índice no está cargado." });
      const n = query === "vacio" ? 0 : Math.min(k, 6);
      send(res, 200, { query, k, results: Array.from({ length: n }, (_, i) => fake(i + 1)) });
    });
    return;
  }
  send(res, 404, { error: "No encontrado." });
}).listen(5000, () => console.log("mock-api en http://localhost:5000"));
