import { test, expect, type Page } from '@playwright/test';

type Hit = Record<string, unknown>;
const hit = (o: Hit = {}): Hit => ({
  track_id: 't1', title: 'Canción Uno', artist: 'Artista', album: 'Álbum', year: 2020,
  genres: ['pop'], popularity: 70, explicit: false, score: 0.8, other_versions: [], ...o,
});

// Mockea POST /api/search; `delay` (ms) retrasa la respuesta para ver el estado de carga.
async function mockSearch(page: Page, status: number, body: object, delay = 0) {
  await page.route('**/api/search', async (route) => {
    if (delay) await new Promise((r) => setTimeout(r, delay));
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  });
}
const ok = (...results: Hit[]) => ({ query: 'q', k: 10, results });
const searchFor = async (page: Page, q: string) => {
  await page.getByTestId('search-input').fill(q);
  await page.getByTestId('search-input').press('Enter');
};

test.describe('API real', () => {
  test('health-status visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('health-status')).toBeVisible();
    await expect(page.getByTestId('health-status')).not.toBeEmpty();
  });

  test('clic en un ejemplo devuelve resultados', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('example-query').first().click();
    const cards = page.getByTestId('result-card');
    await expect(cards.first()).toBeVisible();
    await expect(cards.first().getByTestId('result-title')).not.toBeEmpty();
    await expect(cards.first().getByTestId('result-artist')).not.toBeEmpty();
    await expect(cards.first().getByTestId('result-score')).toBeVisible();
  });

  for (const q of ['canciones tranquilas para estudiar', 'upbeat 90s rock songs']) {
    test(`Enter con consulta "${q}"`, async ({ page }) => {
      await page.goto('/');
      await searchFor(page, q);
      const cards = page.getByTestId('result-card');
      await expect(cards.first()).toBeVisible();
      // puntaje en [0,1]: primer número del texto (admite 0.82, 0,82 o 82 %)
      const txt = (await cards.first().getByTestId('result-score').innerText()).replace(',', '.');
      const n = parseFloat(txt.match(/\d+(\.\d+)?/)![0]);
      const score = txt.includes('%') ? n / 100 : n;
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(1);
    });
  }
});

test.describe('API simulada', () => {
  test('0 resultados → estado vacío', async ({ page }) => {
    await mockSearch(page, 200, ok());
    await page.goto('/');
    await searchFor(page, 'nada');
    await expect(page.getByTestId('state-empty')).toBeVisible();
    await expect(page.getByTestId('result-card')).toHaveCount(0);
  });

  for (const [status, msg] of [[503, 'Índice no cargado: reintenta en unos segundos.'], [400, 'La consulta no puede estar vacía.']] as const) {
    test(`error ${status} muestra el mensaje del backend`, async ({ page }) => {
      await mockSearch(page, status, { error: msg });
      await page.goto('/');
      await searchFor(page, 'x');
      await expect(page.getByTestId('state-error')).toContainText(msg);
    });
  }

  test('caída de red → estado de error', async ({ page }) => {
    await page.route('**/api/search', (route) => route.abort());
    await page.goto('/');
    await searchFor(page, 'x');
    await expect(page.getByTestId('state-error')).toBeVisible();
  });

  test('estado de carga mientras la respuesta se retrasa', async ({ page }) => {
    await mockSearch(page, 200, ok(hit()), 1500);
    let calls = 0;
    page.on('request', (r) => { if (r.url().endsWith('/api/search')) calls++; });
    await page.goto('/');
    await searchFor(page, 'x');
    await expect(page.getByTestId('state-loading')).toBeVisible();
    // mientras carga no se lanza otra búsqueda: una respuesta vieja pisaría a la nueva
    await expect(page.getByTestId('search-button')).toBeDisabled();
    await expect(page.getByTestId('example-query').first()).toBeDisabled();
    await page.getByTestId('search-input').press('Enter');
    await expect(page.getByTestId('result-card')).toBeVisible();
    expect(calls).toBe(1);
    await expect(page.getByTestId('state-loading')).toHaveCount(0);
    await expect(page.getByTestId('example-query').first()).toBeEnabled();
  });

  test('other_versions: el toggle abre y cierra la lista', async ({ page }) => {
    await mockSearch(page, 200, ok(hit({ other_versions: [{ track_id: 'v2', album: 'Deluxe', year: 2021, score: 0.7 }] })));
    await page.goto('/');
    await searchFor(page, 'x');
    const card = page.getByTestId('result-card');
    const list = card.getByTestId('other-versions-list');
    await expect(list).toBeHidden();
    await card.getByTestId('other-versions-toggle').click();
    await expect(list).toBeVisible();
    await expect(list).toContainText('Deluxe');
    await card.getByTestId('other-versions-toggle').click();
    await expect(list).toBeHidden();
  });

  test('sin other_versions no hay toggle', async ({ page }) => {
    await mockSearch(page, 200, ok(hit()));
    await page.goto('/');
    await searchFor(page, 'x');
    await expect(page.getByTestId('result-card')).toBeVisible();
    await expect(page.getByTestId('other-versions-toggle')).toHaveCount(0);
  });

  test('artist/album/year nulos: no aparece "null"', async ({ page }) => {
    await mockSearch(page, 200, ok(hit({ artist: null, album: null, year: null })));
    await page.goto('/');
    await searchFor(page, 'x');
    const card = page.getByTestId('result-card');
    await expect(card).toBeVisible();
    expect(await card.innerText()).not.toMatch(/null|undefined|NaN/i);
  });

  test('explícito visible solo si explicit:true', async ({ page }) => {
    await mockSearch(page, 200, ok(hit({ track_id: 'a', explicit: true }), hit({ track_id: 'b', title: 'Limpia', explicit: false })));
    await page.goto('/');
    await searchFor(page, 'x');
    const cards = page.getByTestId('result-card');
    await expect(cards).toHaveCount(2);
    await expect(cards.nth(0).getByTestId('result-explicit')).toBeVisible();
    await expect(cards.nth(1).getByTestId('result-explicit')).toHaveCount(0);
  });

  test('género vacío no rompe la tarjeta ni muestra "null"', async ({ page }) => {
    await mockSearch(page, 200, ok(hit({ genres: [] })));
    await page.goto('/');
    await searchFor(page, 'x');
    const card = page.getByTestId('result-card');
    await expect(card.getByTestId('result-genres')).toBeVisible();
    expect(await card.innerText()).not.toMatch(/null|undefined/i);
  });
});

test.describe('Entrada', () => {
  test('límite de 300 caracteres', async ({ page }) => {
    await page.goto('/');
    const input = page.getByTestId('search-input');
    await input.fill('a'.repeat(400));
    expect((await input.inputValue()).length).toBeLessThanOrEqual(300);
  });

  test('consulta vacía: botón y Enter no rompen nada ni llaman a la API', async ({ page }) => {
    let calls = 0;
    await page.route('**/api/search', (route) => { calls++; return route.abort(); });
    await page.goto('/');
    await page.getByTestId('search-button').click();
    await page.getByTestId('search-input').press('Enter');
    await expect(page.getByTestId('search-input')).toBeVisible();
    await expect(page.getByTestId('result-card')).toHaveCount(0);
    expect(calls).toBe(0);
  });
});

test.describe('Móvil 375x812', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('sin scroll horizontal y botones táctiles ≥44 px', async ({ page }) => {
    await mockSearch(page, 200, ok(hit({ other_versions: [{ track_id: 'v', album: 'A', year: 2021, score: 0.5 }] })));
    await page.goto('/');
    await searchFor(page, 'x');
    await expect(page.getByTestId('result-card')).toBeVisible();
    const noOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    expect(noOverflow).toBe(true);
    const buttons = page.getByRole('button');
    const n = await buttons.count();
    expect(n).toBeGreaterThan(0);
    for (let i = 0; i < n; i++) {
      const box = await buttons.nth(i).boundingBox();
      if (box) expect.soft(box.height, `botón #${i}`).toBeGreaterThanOrEqual(44);
    }
  });
});

test.describe('Teclado', () => {
  test('buscar solo con teclado y foco visible', async ({ page }) => {
    await mockSearch(page, 200, ok(hit()));
    await page.goto('/');
    const input = page.getByTestId('search-input');
    await input.focus();
    await expect(input).toBeFocused();
    const visible = await input.evaluate((el) => {
      const s = getComputedStyle(el);
      return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none';
    });
    expect(visible).toBe(true);
    await page.keyboard.type('jazz');
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('result-card')).toBeVisible();
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true);
  });
});
