// The live Question bank hung for Vercel's full five minutes on every click (ADR 0024): through
// Supabase's transaction pooler, a third query stacked on one connection never answers. This asks
// eight questions at once through that pooler, with the app's own `lib/db.ts` exactly as a Vercel
// function builds it, and fails if any of them has not answered within 15 seconds.
//   cd apps/web && node scripts/check-pooler.ts
// It only runs `select now()` — nothing is read from or written to any table. The query carries no
// value on purpose: postgres.js waits after a query with values (it asks the server for their
// types first), so only value-less queries stack — and the Question bank's counts are value-less.
import { existsSync } from "node:fs";
import path from "node:path";

const rootEnv = path.resolve(import.meta.dirname, "../../../.env");
if (!process.env.DATABASE_URL && existsSync(rootEnv)) process.loadEnvFile(rootEnv);
if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL is not set — the check needs the live database's address.");
  process.exit(1);
}
// The road a deployed page takes: the transaction pooler, in a serverless function.
process.env.DATABASE_URL = process.env.DATABASE_URL.replace(":5432/", ":6543/");
process.env.VERCEL = "1";

const { sql } = await import("../lib/db.ts");
const N = 8;
let answered = 0;
const timer = setTimeout(() => {
  console.error(`${answered} of ${N} answered after 15 s — queries stacked on one connection are hanging (ADR 0024)`);
  process.exit(1);
}, 15_000);

await Promise.all(Array.from({ length: N }, () => sql`select now() as n`.then(() => answered++)));
clearTimeout(timer);
console.log(`${answered} of ${N} answered`);
await sql.end();
