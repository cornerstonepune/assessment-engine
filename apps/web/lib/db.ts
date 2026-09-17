// The only Postgres connection in the app. Server modules only: never import from a client component.
import { existsSync } from "node:fs";
import path from "node:path";
import postgres from "postgres";

// The repo's single .env lives two levels up; Next only reads apps/web/.env*. Node 24 loads it natively.
if (!process.env.DATABASE_URL) {
  const rootEnv = path.resolve(process.cwd(), "../../.env");
  if (existsSync(rootEnv)) process.loadEnvFile(rootEnv);
}

function connect() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set — see .env.example at the repo root");
  return postgres(url, { ssl: "require", max: 3, prepare: false, idle_timeout: 20 });
}

declare global {
  var cornerstoneSql: ReturnType<typeof postgres> | undefined;
}

// One pool per process; dev's hot reload would otherwise open a new one per edit.
export const sql = globalThis.cornerstoneSql ?? connect();
if (process.env.NODE_ENV !== "production") globalThis.cornerstoneSql = sql;
