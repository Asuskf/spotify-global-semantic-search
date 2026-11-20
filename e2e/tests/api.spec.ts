import { test, expect, type APIRequestContext } from '@playwright/test';

const search = (request: APIRequestContext, data: object) => request.post('/api/search', { data });

test('health: estado ok y vectores indexados', async ({ request }) => {
  const r = await request.get('/api/health');
  expect(r.status()).toBe(200);
  const b = await r.json();
  expect(b.status).toBe('ok');
  expect(typeof b.model).toBe('string');
  expect(b.n_vectors).toBeGreaterThan(0);
  expect(typeof b.gold_run_id).toBe('string');
});

test('búsqueda válida: forma de cada resultado', async ({ request }) => {
  const r = await search(request, { query: 'chill acoustic songs for studying', k: 5 });
  expect(r.status()).toBe(200);
  const b = await r.json();
  expect(b.query).toBe('chill acoustic songs for studying');
  expect(b.k).toBe(5);
  expect(b.results.length).toBeGreaterThanOrEqual(1);
  expect(b.results.length).toBeLessThanOrEqual(5);
  for (const x of b.results) {
    expect(typeof x.track_id).toBe('string');
    expect(typeof x.title).toBe('string');
    expect(x.artist === null || typeof x.artist === 'string').toBe(true);
    expect(x.album === null || typeof x.album === 'string').toBe(true);
    expect(x.year === null || Number.isInteger(x.year)).toBe(true);
    expect(Array.isArray(x.genres)).toBe(true);
    expect(typeof x.popularity).toBe('number');
    expect(typeof x.explicit).toBe('boolean');
    expect(x.score).toBeGreaterThanOrEqual(0);
    expect(x.score).toBeLessThanOrEqual(1);
    expect(Array.isArray(x.other_versions)).toBe(true);
    for (const v of x.other_versions) {
      expect(typeof v.track_id).toBe('string');
      expect(typeof v.score).toBe('number');
    }
  }
});

for (const k of [0, 51]) {
  test(`k=${k} fuera de rango → 400 con error`, async ({ request }) => {
    const r = await search(request, { query: 'rock', k });
    expect(r.status()).toBe(400);
    expect(typeof (await r.json()).error).toBe('string');
  });
}

test('consulta vacía → 400 con error', async ({ request }) => {
  const r = await search(request, { query: '', k: 5 });
  expect(r.status()).toBe(400);
  expect((await r.json()).error).toBeTruthy();
});

test('300 caracteres → 200; 301 → 400', async ({ request }) => {
  expect((await search(request, { query: 'a'.repeat(300), k: 1 })).status()).toBe(200);
  const r = await search(request, { query: 'a'.repeat(301), k: 1 });
  expect(r.status()).toBe(400);
  expect((await r.json()).error).toBeTruthy();
});
