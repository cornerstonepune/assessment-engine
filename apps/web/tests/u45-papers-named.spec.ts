/**
 * U45 — A paper named by what it tests (goals/ux8b-papers-named.yaml). Nimish, 2026-10-21: "focus on the UI/UX first,
 * on whatever we have right now for math, making sure that every screen and every other representation is thought
 * through well: it's clear, it's accurate, clickability is fine."
 *
 * A Grade 2 class of the test's own, made once and kept (evidence is append-only): Asha's copy of a library worksheet on
 * 2-digit + 2-digit at Medium is read, one answer waiting for a person, and has no date; the class has a practice paper
 * this week, planned for Asha. The educator teaches the class. Every page an educator opens the paper from names it by
 * its skill and level, never by the worksheet's code.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek } from "../lib/week";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U45-MINE";
const THIS = isoWeek();
const QR = { read: "CS45A001", practice: "CS45A0P1" };
const NAME = "2-digit + 2-digit · Medium";
const EDUCATOR = { email: "u45-educator@cornerstone.test", name: "U45 Educator", role: "educator", classes: [SECTION] };
const PASSWORD = "u45-a-long-test-password";
const SALT = "45112233445566778899aabbccddeeff";
let kids: Record<string, string>;
let sheet: string;
let code: string;

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const [ws] = await sql<{ id: string; item_ids: string[]; code: string }[]>`
    select id, item_ids, code from sheet_template
    where source = 'library' and retired_at is null and skill_set_code = 'ADD.2D2D' and difficulty = 'Medium' order by code limit 1`;
  code = ws.code;
  ({ sheet } = await aReadPaper(sql, {
    qr: QR.read,
    child: kids.Asha,
    template: ws.id,
    items: ws.item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  }));
  await sql`delete from prescription where child_id = ${kids.Asha} and week = ${THIS} and kind = 'practice'`;
  await sql`delete from sheet_instance where qr_code = ${QR.practice}`;
  const [{ id: practice }] = await sql<{ id: string }[]>`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, section, week, kind, print_status)
    values (${tenant}, ${QR.practice}, ${ws.id}, ${kids.Asha}, ${SECTION}, ${THIS}, 'practice', 'new') returning id`;
  await sql`
    insert into prescription (tenant_id, child_id, week, kind, rule_fired, skill_set_code, difficulty, sheet_instance_id)
    values (${tenant}, ${kids.Asha}, ${THIS}, 'practice', 'band_default', 'ADD.2D2D', 'Medium', ${practice})`;
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`delete from prescription where child_id = ${kids.Asha} and week = ${THIS} and kind = 'practice'`;
  await sql`delete from sheet_instance where qr_code = ${QR.practice}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const page = await (await browser.newContext({ storageState: { cookies: [], origins: [] } })).newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

test("a paper is named by what it tests on every page an educator opens it from", async ({ browser }) => {
  const page = await asEducator(browser);
  for (const path of ["/capture", `/capture/${sheet}`, "/capture/check", `/growth/${kids.Asha}`, `/worksheets/${QR.read}`,
                      `/papers/approve?section=${SECTION}&week=${THIS}&kind=practice`]) {
    await page.goto(path);
    const main = page.locator("main");
    // the page itself first: a "not" passes at once on the loading screen
    if (path.startsWith("/papers")) await expect(main.getByRole("link", { name: "See the paper" })).toBeVisible();
    else await expect(main, path).toContainText(NAME);
    await expect(main, `${path} names the worksheet by its code`).not.toContainText(code);
  }
  await page.context().close();
});

test("one skill has one name: the marking page's lanes are the skills every other page names", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto(`/capture/${sheet}`);
  const lanes = page.locator("section.panel", { has: page.getByRole("heading", { name: "What this paper says, by skill" }) });
  await expect(lanes.getByRole("heading", { level: 3 })).toHaveText(["2-digit + 2-digit"]);
  await page.context().close();
});

test("a paper with no date says nothing of one", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto(`/capture/${sheet}`);
  // the page itself first: a "not" passes at once on the loading screen
  await expect(page.locator("main header")).toContainText("answers on 1 page");
  await expect(page.locator("main header")).not.toContainText(/Sat\s*—/);
  await page.goto("/capture/check");
  await expect(page.locator("main")).toContainText("Asha");
  await expect(page.locator("main")).not.toContainText(/sat\s*—/i);
  await page.context().close();
});

test("a link is named as the page it opens, and that page's way back names where it goes", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto(`/make/${SECTION}`);
  await page.getByRole("link", { name: "What the class did this week" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(`${SECTION} · what the class did this week`);
  await expect(page.getByRole("link", { name: `← ${SECTION} · home assessments` })).toBeVisible();
  await page.context().close();
});

test("a class's home assessments say why a child has none: every child is counted in one column", async ({ page }) => {
  // every class's list is the coordinator's: an educator of one class opens straight on it
  await page.goto("/make");
  const row = page.getByRole("table", { name: "Home assessments this week" }).locator("tbody tr").filter({ hasText: SECTION });
  const n = async (k: string) => Number(await row.locator(`[data-n="${k}"]`).textContent());
  const children = Number(await row.locator("td").nth(2).textContent());
  expect(children).toBe(2);
  expect((await n("proposed")) + (await n("approved")) + (await n("too-few"))).toBe(children);
});
