/**
 * U24 — No page a laundry list (goals/ui6b-no-long-lists.yaml). Nimish, 2026-10-12: "no page should have such laundary
 * lists like stuff". Measured first (STATE.md "UI6 — measured before the build"): a child's every paper, Today's every
 * class pack and parent report, every question ever answered, every week ever planned on Approve papers and every parent
 * report, each in full, one after another. Each now shows what is needed first; the rest is one click away, or narrowed
 * by a choice. The test's own rows are removed after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U24-TEST";
const PACKS = ["U24-P1", "U24-P2", "U24-P3", "U24-P4", "U24-P5", "U24-P6", "U24-P7"];
let kids: Record<string, string> = {};
const mine = (q: string) => q.startsWith("U24T-");

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Esha", "Farid"]);
  // one answer of Esha's is signed off, so her page is the whole page, not her first step
  // (goals/ux4-class-and-child.yaml). Made once: evidence is append-only.
  await sql`
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel, observed_at, confirmed_by)
    select tenant_id, id, 'NUM.OPS.01', 'R21', true, '{}', 'item', now(), 'u24' from child
    where id = ${kids.Esha} and not exists (select 1 from evidence_event where child_id = ${kids.Esha})`;
  const [{ id: template }] = await sql<{ id: string }[]>`
    insert into sheet_template (tenant_id, band, week, item_ids, key)
    select id, 'G2', '2026-W01', '{}'::uuid[], '{"test": "u24"}' from tenant limit 1 returning id`;
  // seven papers for Esha, one a week
  for (let i = 1; i <= 7; i++) {
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by)
      select tenant_id, ${`U24T-E${i}`}, ${template}, id, ${`2026-W0${i}`}, ${SECTION}, 'practice', 'printed', 'e2e'
      from child where id = ${kids.Esha} on conflict do nothing`;
  }
  // a class practice waiting for approval in each of seven classes
  for (const section of PACKS) {
    const one = await aClass(sql, section, "G2", ["Gita"]);
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status)
      select tenant_id, ${`U24T-${section}`}, ${template}, id, '2026-W02', ${section}, 'practice', 'new'
      from child where id = ${one.Gita} on conflict do nothing`;
  }
  // a class plan in each of eight weeks long past
  for (let i = 1; i <= 8; i++) {
    await sql`
      insert into prescription (tenant_id, child_id, week, kind, skill_set_code, difficulty, rule_fired, misconception_targets, strand)
      select tenant_id, id, ${`2025-W1${i}`}, 'practice', 'ADD.2D2D', 'Medium', 'band_default', '{}', 'NUM'
      from child where id = ${kids.Farid} on conflict do nothing`;
  }
});

test.afterAll(async () => {
  const qrs = (await sql<{ qr_code: string }[]>`select qr_code from sheet_instance`).map((r) => r.qr_code).filter(mine);
  await sql`delete from sheet_instance where qr_code = any(${qrs})`;
  await sql`delete from sheet_template where key ->> 'test' = 'u24'`;
  await sql`delete from prescription where child_id = ${kids.Farid} and week like '2025-W1%'`;
  await sql.end();
});

test("a child's page shows their newest papers and opens every one of them on Assessments", async ({ page }) => {
  await page.goto(`/growth/${kids.Esha}`);
  const papers = page.getByRole("region", { name: "Their papers", exact: true });
  await expect(papers.getByRole("listitem")).toHaveCount(5);
  const all = papers.getByRole("link", { name: "Every paper of this child, 7 in all →" });
  await expect(all).toHaveAttribute("href", `/papers?child=${kids.Esha}`);
});

test("Today names the first five classes waiting and opens the rest", async ({ page }) => {
  await page.goto("/today");
  const packs = page.getByRole("region", { name: "Class papers to approve", exact: true });
  const n = Number(await packs.getByTestId("count").innerText());
  expect(n).toBeGreaterThanOrEqual(PACKS.length);
  await expect(packs.getByRole("listitem").filter({ has: page.locator('a[href^="/papers/approve?"]') })).toHaveCount(5);
  await expect(packs.getByRole("link", { name: /^and \d+ more →$/ })).toHaveAttribute("href", "/papers/approve");
});

test("the questions answered are folded under one line until opened", async ({ page }) => {
  const [open] = await sql<{ code: string }[]>`select code from ask where answer is null order by code limit 1`;
  try {
    await sql`update ask set answer = 'agreed', answered_by = 'End-to-end test', answered_at = now() where code = ${open.code}`;
    await page.goto("/asks");
    const answered = page.getByRole("region", { name: "Answered", exact: true });
    const first = answered.getByRole("listitem").first();
    await expect(first).toBeHidden();
    await answered.getByText(/^Read the \d+ answered$/).click();
    await expect(first).toBeVisible();
  } finally {
    await sql`update ask set answer = null, answered_by = null, answered_at = null where code = ${open.code}`;
  }
});

test("Papers to approve chooses a class's week in the filter row, however many weeks there are", async ({ page }) => {
  await page.goto("/papers/approve");
  // no row of a class-and-week tag for every week ever planned: one Week dropdown holds them (goals/uxn4-papers-to-approve.yaml)
  await expect(page.getByRole("navigation", { name: "Classes and weeks" })).toHaveCount(0);
  // the page streams in behind its loading screen: wait for the table before reading the filter row
  await expect(page.getByRole("table", { name: "Each child's paper this week" })).toBeVisible();
  const week = page.locator("[data-filterbar]").getByLabel("Week");
  expect(await week.locator("option").count()).toBeGreaterThanOrEqual(8);
});

test("the parent reports waiting are narrowed by class", async ({ page }) => {
  await page.goto("/growth/reports");
  const table = page.getByRole("table", { name: "Parent reports not up to date" });
  await expect(table).toBeVisible();
  const classes = page.getByRole("navigation", { name: "Class" });
  await expect(classes.getByRole("link", { name: /^Every class/ })).toHaveAttribute("aria-current", "page");
  const one = classes.getByRole("link").nth(1);
  const words = (await one.innerText()).replace(/\s+\d+$/, "");
  await one.click();
  await expect(page).toHaveURL(/[?&]class=/);
  const cells = await table.locator("tbody tr td:nth-child(2)").allInnerTexts();
  expect(cells.length).toBeGreaterThan(0);
  expect(new Set(cells)).toEqual(new Set([words]));
});
