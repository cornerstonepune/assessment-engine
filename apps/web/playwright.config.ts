import { defineConfig } from "@playwright/test";

// One dev server per run: Next 16 locks the project directory, so two cannot coexist. The gate
// tests need the sign-in bypass OFF, so `npm run test:e2e` runs two passes — see package.json.
const BYPASS = process.env.AUTH_DEV_BYPASS ?? "1";

export default defineConfig({
  testDir: "./tests",
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3000", trace: "off" },
  projects: [
    { name: "screens", testMatch: /screens\.spec\.ts/, fullyParallel: true },
    // Shares real database rows with itself, so one worker, in order.
    { name: "e2e", testMatch: /e2e\.spec\.ts/, fullyParallel: false, workers: 1 },
    { name: "gate", testMatch: /gate\.spec\.ts/, fullyParallel: true },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000/login",
    reuseExistingServer: false,
    timeout: 120_000,
    env: { AUTH_DEV_BYPASS: BYPASS },
  },
});
