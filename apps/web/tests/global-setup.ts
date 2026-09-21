// Before any test: a member of staff who exists only in the local copy, and a session cookie for
// them, signed exactly as lib/auth.ts signs one. The tests then use the site the way a person does
// after signing in — no development bypass, which a production build never has.
import { createHmac } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import postgres from "postgres";
import { SIGNED_IN, WEB_PORT } from "../playwright.config";

export const TEST_STAFF = { email: "e2e@cornerstone.test", name: "End-to-end test", role: "coordinator" };

export default async function globalSetup(): Promise<void> {
  const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
  // Only ever the copy: playwright.config.ts has already refused any other address.
  await sql`
    update config set value = value || ${sql.json([TEST_STAFF])}
    where key = 'app.staff' and not value @> ${sql.json([{ email: TEST_STAFF.email }])}`;
  await sql.end();

  const expiry = String(Date.now() + 86_400_000);
  const body = `${Buffer.from(TEST_STAFF.email).toString("base64url")}.${expiry}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  mkdirSync(path.dirname(SIGNED_IN), { recursive: true });
  writeFileSync(
    SIGNED_IN,
    JSON.stringify({
      cookies: [
        {
          name: "cs_staff",
          value: `${body}.${mac}`,
          domain: "localhost",
          path: "/",
          expires: Math.floor(Number(expiry) / 1000),
          httpOnly: true,
          secure: false,
          sameSite: "Lax",
        },
      ],
      origins: [],
    }),
  );
  console.log(`signed in as ${TEST_STAFF.email} on port ${WEB_PORT}`);
}
