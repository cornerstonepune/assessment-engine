/**
 * The sign-in gate, against a server with the development bypass off — the way it runs at school.
 * A gate that is only tested with the bypass on is not tested at all.
 */
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import postgres from "postgres";

const ROUTES = ["/", "/worksheets", "/library", "/capture", "/growth", "/home", "/skill-sets/SUB.2D2D"];

for (const route of ROUTES) {
  test(`no session: ${route} sends you to sign in`, async ({ page }) => {
    await page.goto(route);
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in");
  });
}

// A page's server payload asked for the way the client router asks for it, from a client that says it already holds
// the (app) layout. Next 16's auth guide warns a layout's check does not stop the page rendering into this payload;
// before proxy.ts this request reached Next's own handling (on 2026-10-01 it answered a 500, not data, so the leak was
// never shown). Now nothing without a good session gets that far (goals/p0-every-page-checks-who-asks.yaml).
test("no session: a page's server payload, asked for past its layout, is turned away before the page renders", async ({ request }) => {
  const holding = ["", { children: ["(app)", { children: ["__PAGE__", {}] }] }, null, null, true];
  const res = await request.get("/worksheets", {
    headers: { RSC: "1", "Next-Router-State-Tree": encodeURIComponent(JSON.stringify(holding)) },
    maxRedirects: 0,
  });
  expect(res.status()).toBe(307);
  expect(res.headers()["location"]).toMatch(/\/login$/);
});

test("no session: an API route answers 401 before it reads anything", async ({ request }) => {
  const res = await request.get("/api/see/00000000-0000-0000-0000-000000000000", { maxRedirects: 0 });
  expect(res.status()).toBe(401);
});

test("a wrong password is refused and you stay on the sign-in page", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("School email").fill(`nobody-${randomUUID().slice(0, 8)}@example.com`);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Scoped to main, because Next's own route announcer is also role="alert".
  await expect(page.getByRole("main").getByRole("alert")).toContainText("do not match");
  await expect(page).toHaveURL(/\/login/);
});

test("an email with too many wrong passwords waits, whatever password it tries", async ({ page }) => {
  // goals/p2-live-recovers.yaml: the failures are written as the owner, as many as the limit in force
  const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
  const email = `tries-${randomUUID().slice(0, 8)}@example.com`;
  await sql`
    insert into sign_in_failure (tenant_id, email)
    select t.id, ${email} from tenant t,
      generate_series(1, (select value::int from threshold where key = 'sign_in.max_failures'))
    where t.slug = ${process.env.TENANT_SLUG ?? "cornerstone-pune"}`;
  await page.goto("/login");
  await page.getByLabel("School email").fill(email);
  await page.getByLabel("Password").fill("any-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Too many wrong passwords");
  await sql`delete from sign_in_failure where email = ${email}`;
  await sql.end();
});
