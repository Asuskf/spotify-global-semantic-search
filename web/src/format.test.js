import test from "node:test";
import assert from "node:assert/strict";
import { dash, formatScore, formatGenres } from "./format.js";

test("dash: nulos y vacíos no se muestran como null", () => {
  assert.equal(dash(null), "—");
  assert.equal(dash(undefined), "—");
  assert.equal(dash(""), "—");
  assert.equal(dash(0), "0");
  assert.equal(dash(2014), "2014");
});

test("formatScore: 3 decimales o guion", () => {
  assert.equal(formatScore(0.84321), "0.843");
  assert.equal(formatScore(null), "—");
});

test("formatGenres: lista vacía es 'sin género'", () => {
  assert.equal(formatGenres([]), "sin género");
  assert.equal(formatGenres(["rap", "hip hop"]), "rap, hip hop");
});
