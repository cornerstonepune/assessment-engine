// The only Postgres connection in the app. Server modules only: never import from a client component.
import { existsSync } from "node:fs";
import path from "node:path";
import postgres from "postgres";

// On a developer's machine the repo's single .env lives two levels up, and Next only reads
// apps/web/.env*. On a server there is no file — DATABASE_URL is a real environment variable.
if (!process.env.DATABASE_URL) {
  const rootEnv = path.resolve(process.cwd(), "../../.env");
  if (existsSync(rootEnv)) process.loadEnvFile(rootEnv);
}

// Serverless runs many short-lived instances at once, so each holds a single connection and gives
// it up quickly; a long-lived server can keep a small pool. Deployed, DATABASE_URL must point at
// Supabase's *transaction* pooler (port 6543) — the session pooler keeps one server connection per
// client and a burst of functions will exhaust it. `prepare: false` is what transaction pooling
// requires, and is set either way.
const SERVERLESS = Boolean(process.env.VERCEL || process.env.AWS_LAMBDA_FUNCTION_NAME);

function connect() {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error(
      "DATABASE_URL is not set. Locally: copy .env.example to .env at the repo root. " +
        "On Vercel: add it in Project Settings → Environment Variables, using the transaction " +
        "pooler on port 6543.",
    );
  }
  if (SERVERLESS && url.includes(":5432/")) {
    console.warn(
      "DATABASE_URL uses the session pooler (5432) in a serverless runtime. Use the transaction " +
        "pooler (6543) or connections will run out under load.",
    );
  }
  return postgres(url, {
    ssl: "require",
    prepare: false,
    max: SERVERLESS ? 1 : 3,
    idle_timeout: SERVERLESS ? 5 : 20,
    connect_timeout: 10,
  });
}

declare global {
  var cornerstoneSql: ReturnType<typeof postgres> | undefined;
}

// One pool per process; dev's hot reload would otherwise open a new one on every edit.
export const sql = globalThis.cornerstoneSql ?? connect();
if (process.env.NODE_ENV !== "production") globalThis.cornerstoneSql = sql;
