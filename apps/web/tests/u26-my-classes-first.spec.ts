/**
 * U26 — each person sees their own classes (goals/f1b-my-classes-first.yaml, ADR 0073). Nimish, 2026-10-14: "Then the
 * teachers only see, when Achal logs in, things that are relevant to his grades." An educator linked to one class sees
 * that class's children, papers and what waits on them, and never another's: not in a list, a count or a menu, and not
 * by typing another class's address. The coordinator sees every class. An educator linked to no class yet sees every
 * class and is told why.
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

test("an educator sees their own classes and no other", async ({ browser }) => {
  const page = await signedIn(browser, LINKED.email);
  try {
    // Today and the menu: the other class's pack is not theirs to approve
    await expect(page.getByRole("main")).not.toContainText(OTHER);

    // Children: their class's children, and no one else's
    await page.goto("/growth");
    const children = page.getByRole("table", { name: /: every child$/ });
    await expect(children.first()).toBeVisible();
    await expect(page.getByRole("main")).toContainText("Aarav");
    await expect(page.getByRole("main")).not.toContainText("Chirag");

    // Home assessments, Make papers and Assessments list their class alone
    await page.goto("/make");
    await expect(page.getByRole("main")).toContainText(MINE);
    await expect(page.getByRole("main")).not.toContainText(OTHER);
    await page.goto("/papers/make");
    const classes = await page.getByLabel("Choose a class").locator("option").allTextContents();
    expect(classes.join(" ")).toContain(MINE);
    expect(classes.join(" ")).not.toContain(OTHER);
    await page.goto("/papers?view=papers");
    await expect(page.getByRole("main")).not.toContainText("CSF1B026");

    // another class's page, typed in, says it is not theirs and shows nothing of it
    for (const href of [`/growth/class/${OTHER}`, `/make/${OTHER}`, `/growth/${other.Chirag}`, "/worksheets/CSF1B026"]) {
      await page.goto(href);
      await expect(page.getByRole("main"), href).toContainText("not one of your classes");
      await expect(page.getByRole("main"), href).not.toContainText("Chirag");
    }
    // nor its paper's printed page, its preview, or its print, asked for by address
    for (const href of ["/api/paper/CSF1B026/1", `/api/see/${other.Chirag}?week=2026-W42`, "/api/papers/print?qr=CSF1B026"]) {
      expect((await page.request.get(href)).status(), href).toBe(403);
    }
  } finally {
    await page.context().close();
  }
});

test("the coordinator sees every class", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByRole("main")).toContainText(OTHER);
  await page.goto("/growth");
  await expect(page.getByRole("main")).toContainText("Aarav");
  await expect(page.getByRole("main")).toContainText("Chirag");
  await page.goto(`/growth/class/${OTHER}`);
  await expect(page.getByRole("main")).not.toContainText("not one of your classes");
});

test("an educator linked to no class sees every class and is told why", async ({ browser }) => {
  const page = await signedIn(browser, UNLINKED.email);
  try {
    await expect(page.getByRole("main")).toContainText("No class is linked to you yet");
    await page.goto("/growth");
    await expect(page.getByRole("main")).toContainText("Aarav");
    await expect(page.getByRole("main")).toContainText("Chirag");
  } finally {
    await page.context().close();
  }
});
