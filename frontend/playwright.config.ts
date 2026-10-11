import { defineConfig } from "@playwright/test";

// Smoke test runs the real FastAPI app in fake-runner mode (no API key, no cost) behind `next start`.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || undefined },
  },
  webServer: [
    {
      command:
        "cd ../backend && AI4HUMAN_FAKE_RUNNER=1 AI4HUMAN_DB=/tmp/ai4human-e2e.db python -m uvicorn app.main:app --port 8100",
      url: "http://127.0.0.1:8100/health",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "BACKEND_URL=http://127.0.0.1:8100 npm run build && BACKEND_URL=http://127.0.0.1:8100 npx next start -p 3100",
      url: "http://127.0.0.1:3100",
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
