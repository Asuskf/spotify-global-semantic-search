// E2E del buscador semántico (Playwright, solo Chromium).
//   cd e2e && npm install && npx playwright install chromium     (una vez)
//   npx playwright test                       contra http://localhost:8080 (stack Docker arriba)
//   E2E_BASE_URL=http://host:puerto npx playwright test
//   npx playwright test api.spec.ts           solo contrato de API
//   npx playwright test --list                lista sin ejecutar
//   npx tsc -p .                              tipado
// Trazas y capturas de fallo: e2e/test-results/ (ignorado por git).
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
