/**
 * U26 — each person's pages open on their own classes (goals/f1b-my-classes-first.yaml). From 2026-10-22 to 27 Oct every
 * class's page was every educator's to open (goals/ux9c-one-role.yaml); since 27 Oct a class's children and papers are
 * its own educators' and the coordinator's (goals/own_who_sees_answers.yaml). Nimish: "their assessments, answers to be
 * checked etc. should be restricted to their grade." This file said the reverse until then.
 *
 * The classes are the test's own (tests/rows.ts), made once and kept; the educators are taken off the list after.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U26-MINE";
const OTHER = "U26-OTHER";
const LINKED = { email: "u26-linked@cornerstone.test", name: "U26 Linked", role: "educator", classes: [MINE] };
const UNLINKED = { email: "u26-unlinked@cornerstone.test", name: "U26 Unlinked", role: "educator", classes: [] };
const PASSWORD = "u26-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let other: Record<string, string>;

test.beforeAll(async () => {
  await aClass(sql, MINE, "G2", ["Aarav", "Bela"]);
  other = await aClass(sql, OTHER, "G3", ["Chirag", "Dia"]);
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' not in (${LINKED.email}, ${UNLINKED.email}))
                              || ${sql.json([{ ...LINKED, password }, { ...UNLINKED, password }])}
    where key = 'app.staff'`;
  // a class practice made for the other class and not yet approved: Today and the menu count it for whoever sees it
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  const [had] = await sql`select 1 from sheet_instance where qr_code = 'CSF1B026'`;
  if (!had) {
    const [{ id: template }] = await sql<{ id: string }[]>`
      insert into sheet_template (tenant_id, band, week, item_ids, source) values (${tenant}, 'G3', '2026-W42', '{}', 'generated')
      returning id`;
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status, week, section, kind)
      values (${tenant}, 'CSF1B026', ${template}, ${other.Chirag}, 'new', '2026-W42', ${OTHER}, 'practice')`;
  }
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' not in (${LINKED.email}, ${UNLINKED.email}))
    where key = 'app.staff'`;
  await sql.end();
});

async function signedIn(browser: Browser, email: string): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

test("an educator's pages open on their own class, and another class's pages, children and papers are refused in words", async ({ browser }) => {
  const page = await signedIn(browser, LINKED.email);
  try {
    // where the pages start: their own class
    await page.goto("/growth?view=children");
    await expect(page.getByRole("main")).toContainText("Aarav");
    await expect(page.getByRole("main")).not.toContainText("Chirag");
    // another class's pages, by address, are refused in words, and show nothing of it (goals/own_who_sees_answers.yaml)
    for (const href of [`/growth/class/${OTHER}`, `/make/${OTHER}`, `/growth/${other.Chirag}`]) {
      await page.goto(href);
      await expect(page.getByRole("main"), href).toContainText("not one of your classes");
      await expect(page.getByRole("main"), href).not.toContainText("Chirag");
    }
    await page.goto("/worksheets/CSF1B026");
    await expect(page.getByRole("main")).toContainText("This paper belongs to another class");
    for (const href of ["/api/paper/CSF1B026/1", `/api/see/${other.Chirag}?week=2026-W42`]) {
      expect((await page.request.get(href)).status(), href).toBe(403);
    }
    // no Class box: an educator mapped to one class is shown that class, and every class is the coordinator's view
    await page.goto("/today");
    await expect(page.locator("#bar-class, [data-viewing]")).toHaveCount(0);
  } finally {
    await page.context().close();
  }
});

test("the coordinator sees every class", async ({ page }) => {
  await page.goto(`/today?kind=classpaper&class=${OTHER}`);
  await expect(page.getByRole("main")).toContainText(OTHER);
  await page.goto(`/growth?view=children&class=${MINE}`);
  await expect(page.getByRole("main")).toContainText("Aarav");
  await page.goto(`/growth?view=children&class=${OTHER}`);
  await expect(page.getByRole("main")).toContainText("Chirag");
  await page.goto(`/growth/class/${OTHER}`);
  await expect(page.getByRole("main")).not.toContainText("not one of your classes");
});

test("an educator linked to no class sees no class's children until the coordinator links them", async ({ browser }) => {
  const page = await signedIn(browser, UNLINKED.email);
  try {
    // no class is theirs: none is on the list, and a class's page is refused in words
    await page.goto("/growth?view=children");
    for (const c of [MINE, OTHER]) await expect(page.locator("[data-filterbar] select[name=class] option", { hasText: c })).toHaveCount(0);
    await page.goto(`/growth/class/${MINE}`);
    await expect(page.getByRole("main")).toContainText("not one of your classes");
  } finally {
    await page.context().close();
  }
});
