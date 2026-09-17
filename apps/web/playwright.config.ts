import { defineConfig } from "@playwright/test";

// Runs against a real dev server reading the real database — the screens have no fixtures.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3000", trace: "off" },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
    env: { AUTH_DEV_BYPASS: "1" },
  },
});
