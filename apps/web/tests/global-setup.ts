// Before any test: a member of staff who exists only in the local copy, and a session cookie for
// them, signed exactly as lib/session-cookie.ts signs one (tests/sign-in.ts). The tests then use the site the way a person does
// after signing in — no development bypass, which a production build never has.
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import postgres from "postgres";
import { SIGNED_IN, WEB_PORT } from "../playwright.config";
import { staffCookie } from "./sign-in";

export const TEST_STAFF = { email: "e2e@cornerstone.test", name: "End-to-end test", role: "coordinator" };

export default async function globalSetup(): Promise<void> {
  const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
  // Only ever the copy: playwright.config.ts has already refused any other address.
  await sql`
    update config set value = value || ${sql.json([TEST_STAFF])}
    where key = 'app.staff' and not value @> ${sql.json([{ email: TEST_STAFF.email }])}`;
  await sql.end();

  const cookie = staffCookie(TEST_STAFF.email);
  mkdirSync(path.dirname(SIGNED_IN), { recursive: true });
  writeFileSync(SIGNED_IN, JSON.stringify({ cookies: [cookie], origins: [] }));
  console.log(`signed in as ${TEST_STAFF.email} on port ${WEB_PORT}`);
}
