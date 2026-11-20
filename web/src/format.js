// Campos nulos o vacíos se muestran como "—", nunca como "null".
export const dash = (v) => (v === null || v === undefined || v === "" ? "—" : String(v));

export const formatScore = (s) => (typeof s === "number" ? s.toFixed(3) : "—");

export const formatGenres = (genres) =>
  Array.isArray(genres) && genres.length ? genres.join(", ") : "sin género";
