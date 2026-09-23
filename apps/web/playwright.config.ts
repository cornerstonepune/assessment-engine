import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
import { existsSync } from "node:fs";
import path from "node:path";

// The website as it runs on the public address — a production build, signed in with a real
// session cookie — against the local copy of the database (ADR 0025), never the live one. The live
// Question bank hung for five minutes while every test here passed against a development server
// (ADR 0024); a production build is what pre-loads links and what Vercel runs.
const root = path.resolve(__dirname, "../..");
if (existsSync(path.join(root, ".env"))) process.loadEnvFile(path.join(root, ".env"));
const COPY = process.env.TEST_DATABASE_URL ?? "";
if (!["127.0.0.1", "localhost"].includes(COPY ? new URL(COPY).hostname : "")) {
  throw new Error("TEST_DATABASE_URL must name the local copy (bin/testdb) — refusing to test against any other database");
}
// Every spec that reads rows for itself reads the copy.
process.env.DATABASE_URL = COPY;

export const WEB_PORT = 3100;
export const ENGINE_PORT = 8932;
// Made fresh for each run, in the runner, and inherited by its workers and servers: the servers
// exist for one run on this machine, and no value here is ever a real secret.
process.env.E2E_AUTH_SECRET ??= randomBytes(24).toString("hex");
process.env.E2E_ENGINE_KEY ??= randomBytes(24).toString("hex");
export const SIGNED_IN = path.join(__dirname, "test-results", ".signed-in.json");

export default defineConfig({
  testDir: "./tests",
  reporter: [["list"]],
  // One at a time: the specs share the copy's rows, and the outage tests lock tables every page reads.
  workers: 1,
  globalSetup: "./tests/global-setup.ts",
  use: { baseURL: `http://localhost:${WEB_PORT}`, trace: "off", screenshot: "only-on-failure" },
  projects: [
    { name: "screens", testMatch: /screens\.spec\.ts/, use: { storageState: SIGNED_IN } },
    { name: "e2e", testMatch: /e2e\.spec\.ts/, use: { storageState: SIGNED_IN } },
    { name: "gate", testMatch: /gate\.spec\.ts/ },
    { name: "steps", testMatch: /[su]\d+-[\w-]+\.spec\.ts/, use: { storageState: SIGNED_IN } },
    { name: "map", testMatch: /workflows\.spec\.ts/, use: { storageState: SIGNED_IN } },
  ],
  webServer: [
    {
      command: `.venv/bin/uvicorn engine.api.app:app --port ${ENGINE_PORT}`,
      cwd: path.join(root, "packages/engine"),
      url: `http://127.0.0.1:${ENGINE_PORT}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { DATABASE_URL: COPY, ENGINE_KEY: process.env.E2E_ENGINE_KEY },
    },
    {
      command: `npx next build && npx next start --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}/login`,
      reuseExistingServer: false,
      timeout: 300_000,
      env: {
        NEXT_DIST_DIR: ".next-test",
        DATABASE_URL: COPY,
        ENGINE_URL: `http://127.0.0.1:${ENGINE_PORT}`,
        ENGINE_KEY: process.env.E2E_ENGINE_KEY,
        AUTH_SECRET: process.env.E2E_AUTH_SECRET,
        AUTH_DEV_BYPASS: "0",
      },
    },
  ],
});
