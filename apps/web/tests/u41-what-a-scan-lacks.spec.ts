/**
 * U41 — what a scan lacks is said under Read a scan (goals/l11-a-scan-is-read-whole.yaml). Nimish, 2026-10-16: "a new
 * sheet has been uploaded … the system needs to evaluate and score them". That morning's Grade 3 scan held roll 4's
 * first page twice and roll 1's not at all, and nothing on the site said so.
 *
 * The run is written as the engine writes one (`inbox.read`: each copy's line on `flow_run.result`, by the child's id,
 * never a name), for a class of the test's own. Another class's educator does not see it.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U41-G3";
const OTHER = "U41-G3B";
const FILE = "U41 scan.pdf";
const EDUCATOR = { email: "u41-educator@cornerstone.test", name: "U41 Educator", role: "educator", classes: [OTHER] };
const PASSWORD = "u41-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
const others = sql`(select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s where s ->> 'email' <> ${EDUCATOR.email})`;
let run = "";

test.beforeAll(async () => {
  const kids = await aClass(sql, CLASS, "G3", ["Ana", "Bo"]);
  await aClass(sql, OTHER, "G3", ["Cy", "Di"]);
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`update config set value = ${others} || ${sql.json([{ ...EDUCATOR, password }])} where key = 'app.staff'`;
  const copies = [
    { copy: 1, pages: [2], code: "CS41A001", child_id: kids.Ana, answers: 9, missing: [1], twice: [],
      lacks: ["page 1 of 2 is not in this file: scan it and send it to be read"], notes: [] },
    { copy: 2, pages: [3, 4, 9], code: "CS41A002", child_id: kids.Bo, answers: 21, missing: [],
      twice: [{ page: 1, file_pages: [3, 9] }], lacks: ["page 1 is in the file twice (pages 3 and 9): page 9 is read"], notes: [] },
    { copy: 3, pages: [11], code: "?", child_id: null, answers: 0, skipped: true, why: "no code could be read on the page" },
  ];
  const [t] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  [{ id: run }] = await sql<{ id: string }[]>`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, result)
    values (${t.id}, 'read-scan', ${`u41@cornerstone.test: ${FILE}`}, 'ok', now(), ${sql.json({ copies })}) returning id`;
});
test.afterAll(async () => {
  await sql`delete from flow_run where id = ${run}::uuid`;
  await sql`update config set value = ${others} where key = 'app.staff'`;
  await sql.end();
});

const lacks = (page: Page) =>
  page.getByRole("region", { name: "Read a scan" }).getByRole("list", { name: `What ${FILE} lacks` }).getByRole("listitem");

test("a scan's missing and doubled pages are said under Read a scan, by roll number", async ({ page }) => {
  const said = [
    `${CLASS} · roll 1: page 1 of 2 is not in this file: scan it and send it to be read`,
    `${CLASS} · roll 2: page 1 is in the file twice (pages 3 and 9): page 9 is read`,
    "Copy 3 (page 11): not read — no code could be read on the page",
  ];
  for (const at of ["/capture", "/papers"]) {
    await page.goto(at);
    await expect(lacks(page), `on ${at}`).toHaveText(said);
    const panel = page.getByRole("region", { name: "Read a scan" });
    await expect(panel).toContainText(`${FILE} · `);
    const row = panel.getByRole("table", { name: "Scans read last" }).getByRole("row").filter({ hasText: FILE }).first();
    await expect(row.locator('td[data-label="Copies read"]')).toHaveText("2");
    await expect(row.locator('td[data-label="Answers"]')).toHaveText("30");
    await expect(panel, "a roll number, never a name").not.toContainText(/Ana|Bo\b/);
  }
});

test("another class's educator does not see a scan of a class not theirs", async ({ browser }) => {
  const page = await (await browser.newContext({ storageState: { cookies: [], origins: [] } })).newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  await page.goto("/capture");
  await expect(page.getByRole("region", { name: "Read a scan" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Read a scan" })).not.toContainText(FILE);
});
