/**
 * S44 — Assessments, decluttered (goals/s2b-assessments-declutter.yaml). Nimish reviewed the live page on 2026-10-22:
 * "Look at the clutter", "The current frontend is extremely confusing to me... make it much, much cleaner".
 *
 * A Grade 2 class of the test's own (made once and kept: evidence is append-only), and each run its own assessment, its
 * printed codes new each run. The assessment is one the test knows the answers to: Asha's paper has two answers waiting
 * for a person, Bina's one, Chetan's is not back. A fourth paper, Dev's, was put away after it was read: its answer waits
 * for no one, yet the old list counted it and the check page did not.
 */
import { randomBytes } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { SIGNED_IN } from "../playwright.config";
import { aClass, aReadPaper } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "S44-CLASS";
const RUN = randomBytes(2).toString("hex").toUpperCase();
const code = (n: string) => `CS${RUN}${n}`;
let kids: Record<string, string> = {};
let ws: { id: string; item_ids: string[]; set: string };
let week = "";
let tenant = "";

const card = () => `/papers/card?${new URLSearchParams({ class: SECTION, week, kind: "assessment", set: ws.set })}`;
const number = (s: string | null) => Number((s ?? "").replace(/\D/g, ""));

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan", "Dev"]);
  [{ tenant, week }] = await sql<{ tenant: string; week: string }[]>`
    select tenant_id as tenant, to_char(now(), 'IYYY-"W"IW') as week from child where id = ${kids.Asha}`;
  [ws] = await sql<{ id: string; item_ids: string[]; set: string }[]>`
    select t.id, t.item_ids, t.skill_set_code as set from sheet_template t
    where t.source = 'library' and t.retired_at is null and t.band = 'G2' and cardinality(t.item_ids) >= 2 order by t.code limit 1`;
  // an earlier run's papers are put away, as a paper made in error is: the page holds this run's alone
  await sql`update sheet_instance set print_status = 'void' where section = ${SECTION} and qr_code not like ${`CS${RUN}%`}`;
  const made = { Asha: "C1", Bina: "C2", Chetan: "C3", Dev: "C4" } as const;
  for (const [who, n] of Object.entries(made)) {
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, section, week, kind, print_status,
                                  approved_by, approved_at, printed_at)
      values (${tenant}, ${code(n)}, ${ws.id}, ${kids[who]}, ${SECTION}, ${week}, 'assessment', 'printed', 'e2e', now(), now())`;
  }
  const two = ws.item_ids.slice(0, 2);
  const waits = (read: string) => ({ status: "needs_teacher", read });
  await aReadPaper(sql, { qr: code("C1"), child: kids.Asha, template: ws.id, items: two, reads: [waits("7"), waits("8")] });
  await aReadPaper(sql, { qr: code("C2"), child: kids.Bina, template: ws.id, items: two, reads: [{ status: "correct", read: "1" }, waits("9")] });
  // a paper put away after it was read holds an answer no one can check
  await aReadPaper(sql, { qr: code("C4"), child: kids.Dev, template: ws.id, items: two.slice(0, 1), reads: [waits("3")] });
  await sql`update sheet_instance set print_status = 'void' where qr_code = ${code("C4")}`;
  // an old scan that found nothing, as the live page showed: "WhatsApp Scan … 0 copies found"
  await sql`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, result)
    values (${tenant}, 'read-scan', 's44: WhatsApp Scan 2026-10-21 s44.pdf', 'ok', now(), ${sql.json({ copies: [], pages: 3 })})`;
});
test.afterAll(async () => {
  await sql`delete from flow_run where flow = 'read-scan' and trigger like 's44:%'`;
  await sql.end();
});

test("the upload box is the first thing, and Make an assessment is one button opening the four ways", async ({ page }) => {
  await page.goto("/papers");
  await expect(page.getByText("Choose scans or drop them here").first()).toBeVisible();
  const upload = (await page.getByText("Choose scans or drop them here").first().boundingBox())!;
  await expect(page.locator("[data-week]").first()).toBeVisible();
  const firstWeek = (await page.locator("[data-week]").first().boundingBox())!;
  expect(upload.y, "the upload box sits above the first week").toBeLessThan(firstWeek.y);
  expect(await page.locator("main .panel").first().evaluate((el) => !!el.querySelector("input[type=file]"))).toBe(true);

  // one button; the four ways are inside it, and no longer four cards on the page
  const make = page.getByText("Make an assessment", { exact: true });
  await expect(make).toHaveCount(1);
  await expect(page.getByRole("link", { name: /^For a class/ })).toBeHidden();
  await expect(page.getByText("one assessment for every child of a class")).toHaveCount(0);
  await make.click();
  const ways = ["For a class", "For each child", "For one child", "A ready-made worksheet"];
  for (const w of ways) await expect(page.getByRole("link", { name: new RegExp(`^${w}`) })).toBeVisible();
  await expect(page.getByRole("link", { name: /^For a class/ })).toHaveAttribute("href", /\/papers\/make\?kind=assessment&way=same/);
  await expect(page.getByRole("link", { name: /^A ready-made worksheet/ })).toHaveAttribute("href", "/worksheets");
});

test("no paragraph over 140 characters sits under the title", async ({ page }) => {
  await page.goto("/papers");
  const lines = await page.locator("header p, main p:not(table p)").evaluateAll((ps) =>
    ps.filter((p) => (p as HTMLElement).offsetParent !== null).map((p) => (p.textContent ?? "").trim()),
  );
  expect(lines.length, "a short line may stay").toBeLessThanOrEqual(2);
  for (const l of lines) expect(l.length, l).toBeLessThanOrEqual(140);
  // the old explanatory paragraph is gone
  await expect(page.getByText("An assessment opens to its copies; a copy opens")).toHaveCount(0);
});

test("no zero is drawn, and the stage and topic chips are one Filter", async ({ page }) => {
  await page.goto("/papers");
  await expect(page.getByRole("navigation", { name: "Papers by stage" })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Topic" })).toHaveCount(0);
  const text = await page.locator("main").innerText();
  expect(text, "a zero count is not drawn").not.toMatch(/(^|\s)0\s+(answers?|papers?|copies|to |with |waiting|signed|checked)/i);
  for (const chip of await page.locator("main .chip, main .fact").allInnerTexts()) expect(chip.trim(), "a bare 0").not.toBe("0");

  // the Filter holds what the chips did, as choices that change the list
  const filter = page.getByText("Filter", { exact: true });
  await expect(filter).toHaveCount(1);
  await filter.click();
  for (const name of ["stage", "topic", "class", "child", "kind", "week"]) await expect(page.locator(`[data-filters] select[name=${name}]`)).toBeVisible();
  await page.locator("[data-filters] select[name=stage]").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Show" }).click();
  await expect(page).toHaveURL(/\/papers\?.*stage=/);
});

test("scans already read are behind Past scans, and the reader's record behind its link", async ({ page }) => {
  await page.goto("/papers");
  await expect(page.getByText("WhatsApp Scan")).toHaveCount(0);
  await expect(page.getByText("0 copies found")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Scans, and how the reader is doing" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "How the reader is doing" })).toBeVisible();
  await page.getByRole("link", { name: "Past scans" }).click();
  await expect(page).toHaveURL(/\/capture/);
  await expect(page.getByText("WhatsApp Scan 2026-10-21 s44.pdf").first()).toBeVisible();
});

/** The answers to check each place shows, for this test's own assessment where it can be told apart. */
async function shown(page: Page) {
  await page.goto("/papers");
  const rows = page.locator(`tr[data-assessment^="assessment~${SECTION}~${week}"]`);
  await expect(rows).toHaveCount(1);
  const own = {
    copies: number(await rows.getByTestId("copies").textContent()),
    papersIn: number(await rows.getByTestId("in").textContent()),
    toCheck: number(await rows.getByTestId("to-check").textContent()),
  };
  const listTotal = (await page.getByTestId("to-check").allTextContents()).reduce((n, t) => n + number(t), 0);
  await page.goto(card());
  const onCard = number(await page.getByTestId("to-check").textContent());
  await page.goto("/capture/check");
  const onCheck = number((await page.getByText(/answers? left to check/).textContent())!.match(/(\d[\d,]*)\s+answers? left/)![1]);
  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");
  const region = page.getByRole("region", { name: "Answers to check", exact: true });
  const onToday = (await region.count()) ? number(await region.getByTestId("count").innerText()) : 0;
  return { own, listTotal, onCard, onCheck, onToday };
}

test("copies, papers in and answers to check are each said once on the list", async ({ page }) => {
  await page.goto("/papers");
  const row = page.locator(`tr[data-assessment^="assessment~${SECTION}~${week}"]`);
  // 3 of the 4 papers are this assessment's to count: Asha, Bina, Chetan (Dev's is put away)
  await expect(row.getByTestId("copies")).toHaveText(/3/);
  await expect(row.getByTestId("in")).toHaveText(/2/);
  await expect(row.getByTestId("to-check")).toHaveText(/3/);
  // a number is drawn only where someone must act: nothing waits in "signed off", so it is not drawn
  await expect(row.getByText(/\b0\b/)).toHaveCount(0);
});

test("the list, the card, Check the answers and Today show the same answers to check", async ({ page }) => {
  const s = await shown(page);
  expect(s.own.toCheck, "this assessment: Asha's two and Bina's one").toBe(3);
  expect(s.onCard, "the card says what the list says").toBe(s.own.toCheck);
  expect(s.onCheck, "Check the answers counts what the list adds up to").toBe(s.listTotal);
  expect(s.onToday, "Today counts what Check the answers counts").toBe(s.onCheck);
});

test("on a phone the page is the same few things and does not scroll sideways", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 800 }, storageState: SIGNED_IN });
  const page = await ctx.newPage();
  await page.goto("/papers");
  await expect(page.getByText("Choose scans or drop them here").first()).toBeVisible();
  await expect(page.getByText("Make an assessment", { exact: true })).toBeVisible();
  await expect(page.getByText("Filter", { exact: true })).toBeVisible();
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(wide, "no sideways scroll").toBe(false);
  await expect(page.locator("[data-week]").first()).toBeVisible();
  const upload = (await page.getByText("Choose scans or drop them here").first().boundingBox())!;
  const firstWeek = (await page.locator("[data-week]").first().boundingBox())!;
  expect(upload.y).toBeLessThan(firstWeek.y);
  await ctx.close();
});
