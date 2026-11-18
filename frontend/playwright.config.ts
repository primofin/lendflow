import { defineConfig, devices } from "@playwright/test";

// Browser tests run the real backend against the TEST database, which is wiped and re-seeded
// at start (backend/scripts/e2e_reset.py refuses any database not ending in _test).
// Needs: Postgres up (docker compose up -d --wait) and `uv` on PATH.
const BACKEND_PORT = 8100;
const FRONTEND_PORT = 3100;
const databaseUrl =
  process.env.E2E_DATABASE_URL ??
  "postgresql+psycopg://lendflow:lendflow@localhost:5433/lendflow_test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1, // one shared database
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run python -m scripts.e2e_reset && uv run fastapi run app/main.py --port ${BACKEND_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${BACKEND_PORT}/health`,
      env: {
        DATABASE_URL: databaseUrl,
        TEST_DATABASE_URL: databaseUrl,
        // LF-008: short mock-bureau timings so a browser test finishes in seconds
        CIC_DURATION_SECONDS: "3",
        CIC_ATTEMPT_TIMEOUT_SECONDS: "4",
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT}`,
      url: `http://localhost:${FRONTEND_PORT}`,
      env: { BACKEND_URL: `http://localhost:${BACKEND_PORT}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
