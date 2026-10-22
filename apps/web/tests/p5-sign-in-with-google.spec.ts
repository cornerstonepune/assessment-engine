/**
 * P5 — sign in with Google, school accounts only (goals/a1-sign-in-with-google.yaml). Nimish, 2026-10-22: "the
 * default, irrespective of anything, should be the Cornerstone email ID, so no one can log in without the Cornerstone
 * email ID … sign in using gmail … right now, we just put me as the admin and everyone else as the educator … no one
 * outside of the school is going to have access."
 *
 * First the token's checks, on tokens this file signs itself: lib/google.ts as it runs, with no server. Then the door,
 * with Google faked at the boundary (tests/fake-google.mts): the state, the PKCE verifier, the token's signature and
 * claims, and the school's rule are the website's own code on a production build.
 */
import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { SignJWT, createLocalJWKSet, exportJWK, generateKeyPair, type JWTPayload } from "jose";
import postgres from "postgres";
import { googleConfigured, schoolEmail, verifyIdToken } from "../lib/google";
import { FAKE_GOOGLE } from "../playwright.config";

const DOMAIN = "cornerstoneschool.in";
const CLIENT = "e2e-client.apps.googleusercontent.com";

// ---- the token's checks

const google = generateKeyPair("RS256");
const stranger = generateKeyPair("RS256");

async function token(claims: JWTPayload = {}, signedBy = google): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT({ iss: "https://accounts.google.com", aud: CLIENT, sub: "1", iat: now, exp: now + 3600, ...claims })
    .setProtectedHeader({ alg: "RS256", kid: "google" })
    .sign((await signedBy).privateKey);
}

async function googleKeys() {
  return createLocalJWKSet({ keys: [{ ...(await exportJWK((await google).publicKey)), kid: "google", alg: "RS256" }] });
}

const SCHOOL = { email: `educator@${DOMAIN}`, email_verified: true, hd: DOMAIN };

test("a verified school account of the school's Workspace is let in, by its email", async () => {
  const claims = await verifyIdToken(await token({ ...SCHOOL, email: `Educator@${DOMAIN}` }), CLIENT, await googleKeys());
  expect(schoolEmail(claims, DOMAIN)).toBe(`educator@${DOMAIN}`);
});

test("an email outside the school's domain is refused", async () => {
  const claims = await verifyIdToken(await token({ ...SCHOOL, email: "someone@gmail.com" }), CLIENT, await googleKeys());
  expect(schoolEmail(claims, DOMAIN)).toBeNull();
  // a domain that only ends like the school's is not the school's
  expect(schoolEmail({ ...SCHOOL, email: `someone@not${DOMAIN}` }, DOMAIN)).toBeNull();
});

test("an email Google has not verified is refused", async () => {
  const claims = await verifyIdToken(await token({ ...SCHOOL, email_verified: false }), CLIENT, await googleKeys());
  expect(schoolEmail(claims, DOMAIN)).toBeNull();
  expect(schoolEmail({ ...SCHOOL, email_verified: "true" }, DOMAIN), "only the claim true, never a string").toBeNull();
});

test("an account with no Workspace domain, or another Workspace, is refused", async () => {
  const noHd = { email: SCHOOL.email, email_verified: true };
  expect(schoolEmail(await verifyIdToken(await token(noHd), CLIENT, await googleKeys()), DOMAIN)).toBeNull();
  expect(schoolEmail({ ...SCHOOL, hd: "gmail.com" }, DOMAIN)).toBeNull();
});

test("a token made for another site is refused", async () => {
  await expect(verifyIdToken(await token({ ...SCHOOL, aud: "someone-else" }), CLIENT, await googleKeys())).rejects.toThrow();
});

test("an expired token is refused", async () => {
  const past = Math.floor(Date.now() / 1000) - 7200;
  await expect(verifyIdToken(await token({ ...SCHOOL, iat: past, exp: past + 3600 }), CLIENT, await googleKeys())).rejects.toThrow();
});

test("a token not signed by Google, or not issued by Google, is refused", async () => {
  await expect(verifyIdToken(await token(SCHOOL, stranger), CLIENT, await googleKeys())).rejects.toThrow();
  await expect(verifyIdToken(await token({ ...SCHOOL, iss: "https://evil.example" }), CLIENT, await googleKeys())).rejects.toThrow();
});

test("without the Google secrets, sign-in is not set up", async () => {
  const kept = { id: process.env.GOOGLE_CLIENT_ID, secret: process.env.GOOGLE_CLIENT_SECRET };
  try {
    delete process.env.GOOGLE_CLIENT_ID;
    process.env.GOOGLE_CLIENT_SECRET = "set";
    expect(googleConfigured()).toBe(false);
    process.env.GOOGLE_CLIENT_ID = "set";
    delete process.env.GOOGLE_CLIENT_SECRET;
    expect(googleConfigured()).toBe(false);
    process.env.GOOGLE_CLIENT_SECRET = "set";
    expect(googleConfigured()).toBe(true);
  } finally {
    for (const [k, v] of [["GOOGLE_CLIENT_ID", kept.id], ["GOOGLE_CLIENT_SECRET", kept.secret]] as const) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
});

// ---- the door, Google faked at the boundary

test.describe("through the door", () => {
  test.describe.configure({ mode: "serial" });
  test.use({ storageState: { cookies: [], origins: [] } });
  const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
  const made: string[] = [];

  test.afterAll(async () => {
    await sql`
      update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                                 where not (s ->> 'email' = any(${made})))
      where key = 'app.staff'`;
    await sql.end();
  });

  function schoolAccount(name: string) {
    const email = `p5-${randomUUID().slice(0, 8)}@${DOMAIN}`;
    made.push(email);
    return { email, email_verified: true, hd: DOMAIN, name };
  }

  async function signInWithGoogle(page: Page, account: JWTPayload): Promise<void> {
    const res = await fetch(`${FAKE_GOOGLE}/as`, { method: "POST", body: JSON.stringify(account) });
    expect(res.ok).toBe(true);
    await page.goto("/login");
    await page.getByRole("link", { name: "Sign in with Google" }).click();
  }

  async function staffRow(email: unknown) {
    const [row] = await sql<{ value: Record<string, unknown> }[]>`
      select s as value from config, jsonb_array_elements(value) s where key = 'app.staff' and s ->> 'email' = ${String(email)}`;
    return row?.value;
  }

  test("the sign-in page asks for no password, only the school Google account", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in");
    await expect(page.getByRole("link", { name: "Sign in with Google" })).toBeVisible();
    await expect(page.locator("input[type=password]")).toHaveCount(0);
  });

  test("someone outside the school is refused with a plain page, and is put on no list", async ({ page }) => {
    const email = `p5-${randomUUID().slice(0, 8)}@gmail.com`;
    await signInWithGoogle(page, { email, email_verified: true, name: "Not School" });
    await expect(page).toHaveURL(/\/login\?error=school$/);
    await expect(page.getByRole("main").getByRole("alert")).toHaveText("Use your Cornerstone school Google account.");
    expect(await staffRow(email)).toBeUndefined();
    await page.goto("/today");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("a school account signs in with Google and lands on Today", async ({ page }) => {
    await signInWithGoogle(page, schoolAccount("P5 Lands"));
    await expect(page).toHaveURL(/\/today$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");
    await expect(page.getByRole("complementary").getByRole("group", { name: "Signed in" })).toContainText("P5 Lands");
  });

  test("a school email new to the list joins it as an educator, with no form", async ({ page }) => {
    const account = schoolAccount("P5 New Educator");
    expect(await staffRow(account.email)).toBeUndefined();
    await signInWithGoogle(page, account);
    await expect(page).toHaveURL(/\/today$/);
    expect(await staffRow(account.email)).toEqual({ email: account.email, name: "P5 New Educator", role: "educator", classes: [] });
  });

  test("the coordinator put on the list by engine staff add keeps the role on signing in", async ({ page }) => {
    const account = schoolAccount("P5 Coordinator");
    const row = { email: account.email, name: "P5 Coordinator", role: "coordinator", classes: [] };
    await sql`update config set value = value || ${sql.json([row])} where key = 'app.staff'`;
    await signInWithGoogle(page, { ...account, name: "A Different Google Name" });
    await expect(page).toHaveURL(/\/today$/);
    expect(await staffRow(account.email), "the row is as it was: role, name and classes").toEqual(row);
  });

  test("a sign-in this browser did not start is refused", async ({ page }) => {
    await page.goto("/login/google/callback?code=made-up&state=made-up");
    await expect(page).toHaveURL(/\/login\?error=failed$/);
    await expect(page.getByRole("main").getByRole("alert")).toHaveText("Google did not finish signing you in. Try again.");
  });
});
