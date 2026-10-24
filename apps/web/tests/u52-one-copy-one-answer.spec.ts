/**
 * U52 — One copy a child, one line an answer, and the two readings told apart (goals/dup_answers_listed_twice.yaml).
 * Nimish, 2026-10-23, after reading a Grade 1 file again and checking all 120 answers: "why are there duplicate entries"
 * and "if there are blank answers, why is the system considering this as right?"
 *
 * A Grade 2 class of the test's own, its educator signed in, one class assessment this week on a skill whose questions
 * each test two registry skills:
 * - Asha's copy read and signed off (three answers: one the reader read as a number, one the reader saw nothing in and a
 *   person typed 10, one the reader read and a person judged), and a second copy of hers, printed, never handed back;
 * - Bina's copy read, every answer blank, not signed off; Chetan's copy printed, one copy only;
 * - Dev's copy read, every answer wrong.
 * What each screen counts is read back and recomputed here from the rows, not taken from the screen.
 */
import { scryptSync } from "node:crypto";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek } from "../lib/week";

// with SHOTS set the tests run apart, so a picture is kept of each screen even where an earlier check fails
test.describe.configure({ mode: process.env.SHOTS ? "default" : "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U52-CLASS";
const THIS = isoWeek();
const QR = { asha: "CS520A01", ashaTwin: "CS520A02", bina: "CS520B01", chetan: "CS520C01", dev: "CS520D01" };
const EDUCATOR = { email: "u52-educator@cornerstone.test", name: "U52 Educator", role: "educator", classes: [SECTION] };
const PASSWORD = "u52-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let kids: Record<string, string> = {};
let skill = "";
let ashaCapture = "";

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan", "Dev"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  // a skill whose questions test two registry skills each, with two library worksheets
  const ws = await sql<{ id: string; item_ids: string[]; skill: string }[]>`
    select t.id, t.item_ids, t.skill_set_code as skill from sheet_template t
    where t.source = 'library' and t.retired_at is null and cardinality(t.item_ids) >= 3
      and t.skill_set_code = (select s.code from skill s join sheet_template w on w.skill_set_code = s.code
                              and w.source = 'library' and w.retired_at is null
                              where cardinality(s.registry_codes) >= 2 group by s.code having count(*) >= 2 order by s.code limit 1)
    order by t.code limit 3`;
  [{ name: skill }] = await sql<{ name: string }[]>`select name from skill where code = ${ws[0].skill}`;
  const onThePack = (qr: string) => sql`
    update sheet_instance set week = ${THIS}, section = ${SECTION}, kind = 'assessment', approved_by = 'u52', approved_at = now()
    where qr_code = ${qr}`;
  const asha = await aReadPaper(sql, {
    qr: QR.asha,
    child: kids.Asha,
    template: ws[0].id,
    items: ws[0].item_ids.slice(0, 3),
    reads: [
      { status: "correct", read: "8" },
      { status: "correct", read: "" },
      { status: "correct", read: "4", checkedBy: "u52" },
    ],
  });
  ashaCapture = asha.capture;
  // the reader writes each answer's number on its page into its reading; a worksheet's questions carry none of their own
  for (const [i, id] of asha.results.entries()) {
    await sql`update item_result set raw_read = (raw_read::jsonb || ${sql.json({ slot: String(i + 1) })})::text where id = ${id}`;
  }
  // the reader saw nothing in the second box; a person looked at the page and typed what the child wrote
  await sql`
    insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by)
    values (${tenant}, ${kids.Asha}, ${asha.capture}, ${asha.results[1]}, '', '10', 'u52')`;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${tenant}, ${QR.ashaTwin}, ${ws[1].id}, ${kids.Asha}, ${THIS}, ${SECTION}, 'assessment', 'printed', 'u52', now()
    where not exists (select 1 from sheet_instance where qr_code = ${QR.ashaTwin})`;
  await aReadPaper(sql, {
    qr: QR.bina,
    child: kids.Bina,
    template: ws[0].id,
    items: ws[0].item_ids.slice(0, 3),
    reads: [{ status: "blank", checkedBy: "u52" }, { status: "blank", checkedBy: "u52" }, { status: "blank", checkedBy: "u52" }],
  });
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${tenant}, ${QR.chetan}, ${ws[2].id}, ${kids.Chetan}, ${THIS}, ${SECTION}, 'assessment', 'printed', 'u52', now()
    where not exists (select 1 from sheet_instance where qr_code = ${QR.chetan})`;
  await aReadPaper(sql, {
    qr: QR.dev,
    child: kids.Dev,
    template: ws[1].id,
    items: ws[1].item_ids.slice(0, 3),
    reads: [
      { status: "wrong", read: "1", checkedBy: "u52" },
      { status: "wrong", read: "2", checkedBy: "u52" },
      { status: "wrong", read: "3", checkedBy: "u52" },
    ],
  });
  for (const qr of [QR.asha, QR.bina, QR.dev]) await onThePack(qr);
  await sql`select confirm_results(${kids.Asha}::uuid, 'u52', ${asha.capture}::uuid)`;
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] }, viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

// SHOTS=<dir> keeps a 1440 px picture of each screen, for the before and after of a change
async function shoot(page: Page, name: string) {
  if (!process.env.SHOTS) return;
  mkdirSync(process.env.SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(process.env.SHOTS, `${name}.png`), fullPage: true });
}

const opened = async (page: Page) => {
  await page.goto(`/papers?class=${SECTION}`);
  // a class's one assessment opens by itself when the filters leave only it; a click would close it again
  const line = page.locator(`[data-assessment]`).getByRole("link", { name: skill });
  if ((await line.getAttribute("aria-expanded")) !== "true") await line.click();
  const copies = page.getByRole("table", { name: `${skill}: each copy` });
  await expect(copies).toBeVisible();
  return copies;
};

test("an assessment shows each child once; a copy never handed back beside a read one is said in words, not listed as a second child", async ({ browser }) => {
  const page = await asEducator(browser);
  const copies = await opened(page);
  await shoot(page, "papers-assessment");
  const names = await copies.locator("tbody tr").evaluateAll((trs) => trs.map((t) => t.querySelectorAll("td")[1].textContent?.trim()));
  expect(names).toEqual(["Asha", "Bina", "Chetan", "Dev"]);
  // Asha's read copy is the one listed, with its score; her second copy is said under the table
  const asha = copies.locator("tbody tr", { hasText: "Asha" });
  await expect(asha).toContainText("3 of 3");
  await expect(page.locator("[data-extras]")).toHaveText(/1 extra copy of a child who has already handed theirs in, not read:\s*CS520A02/);
  // the assessment's own line counts the children's copies, not the extra: four children, so no step reads "of 5"
  await expect(page.locator("[data-assessment]").first()).not.toContainText(/of 5\b/);
  // …and the score across copies counts Asha's answers once
  await page.context().close();
});

test("a copy whose answers are all blank, or none right, says so beside its score", async ({ browser }) => {
  const page = await asEducator(browser);
  const copies = await opened(page);
  await expect(copies.locator("tbody tr", { hasText: "Bina" }).locator("[data-warn]")).toHaveText(/every answer blank.*right page/i);
  await expect(copies.locator("tbody tr", { hasText: "Dev" }).locator("[data-warn]")).toHaveText(/none right.*right page/i);
  await expect(copies.locator("tbody tr", { hasText: "Asha" }).locator("[data-warn]")).toHaveCount(0);
  await page.context().close();
});

test("a child's page lists each answer once, and every count on it is the answers', recomputed from the rows", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto(`/growth/${kids.Asha}`);
  await shoot(page, "child-page");
  // independent of the screen: the answers signed off, and what each skill has of them
  const [{ n }] = await sql<{ n: number }[]>`
    select count(distinct item_result_id)::int as n from evidence_event e
    join item_result r on r.id = e.item_result_id join capture c on c.id = r.capture_id
    where e.child_id = ${kids.Asha} and e.confirmed_by is not null and c.superseded_by is null`;
  expect(n).toBe(3);
  await expect(page.getByText(/\b3 answers signed off over 1 paper\b/)).toBeVisible();
  const skills = await sql<{ skill: string; events: number; right: number }[]>`
    select e.skill_code as skill, count(distinct e.item_result_id)::int as events,
           count(distinct e.item_result_id) filter (where e.correct)::int as right
    from evidence_placed e join item_result r on r.id = e.item_result_id join capture c on c.id = r.capture_id
    where e.child_id = ${kids.Asha} and e.confirmed_by is not null and c.superseded_by is null group by 1`;
  expect(skills.length).toBeGreaterThanOrEqual(2);
  // the graph counts an answer once on each skill it tests, never twice on one
  const state = await sql<{ skill: string; n_events: number; n_correct: number }[]>`
    select skill_code as skill, n_events, n_correct from child_skill_state where child_id = ${kids.Asha}`;
  for (const s of skills) expect(state.find((x) => x.skill === s.skill)).toMatchObject({ n_events: s.events, n_correct: s.right });
  // every table of answers on the page names a question once
  await page.locator("details").evaluateAll((ds) => ds.forEach((d) => d.setAttribute("open", "")));
  const tables = page.locator("[data-skill] table");
  expect(await tables.count()).toBeGreaterThan(0);
  for (const t of await tables.all()) {
    const slots = await t.locator("tbody tr td:nth-child(2)").allTextContents();
    expect(slots.length).toBe(new Set(slots).size);
  }
  // a skill's line counts what its own table lists
  const lines = await page.locator("[data-skill][data-of]").evaluateAll((els) => els.map((e) => e.getAttribute("data-of")!));
  expect(lines.length).toBeGreaterThan(0);
  for (const of of lines) {
    const s = skills.find((x) => x.skill === of)!;
    const line = page.locator(`[data-skill][data-of="${of}"]`).first();
    await expect(line).toContainText(`${s.right} of ${s.events} right`);
    await expect(line.locator("tbody tr")).toHaveCount(s.events);
  }
  await page.context().close();
});

test("the two readings are told apart by header and by words: what the reader saw, what the child wrote you confirmed", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto(`/growth/${kids.Asha}`);
  await page.locator("details").evaluateAll((ds) => ds.forEach((d) => d.setAttribute("open", "")));
  // the skill every one of the three questions tests
  const lines = await page.locator("[data-skill][data-of]").evaluateAll((els) => els.map((e) => e.getAttribute("data-of")!));
  const [{ skill: common }] = await sql<{ skill: string }[]>`
    select e.skill_code as skill from evidence_placed e join item_result r on r.id = e.item_result_id
    join capture c on c.id = r.capture_id
    where e.child_id = ${kids.Asha} and e.confirmed_by is not null and c.superseded_by is null
      and e.skill_code = any(${lines})
    group by 1 having count(distinct e.item_result_id) = 3 order by 1 limit 1`;
  const table = page.locator(`[data-skill][data-of="${common}"] table`).first();
  await expect(table.locator("thead th")).toHaveText([
    "Date",
    "Q",
    "Question",
    "What the reader saw",
    "What the child wrote (you confirmed)",
    "Right answer",
    "Mark",
    "Mistake matched",
  ]);
  const row = (q: string) => table.locator("tbody tr", { has: page.locator("td.fact", { hasText: new RegExp(`^${q}$`) }) });
  await expect(row("1").locator("td").nth(3)).toHaveText("8");
  await expect(row("1").locator("td").nth(4)).toHaveText("8");
  // the reader saw nothing, a person typed 10: both said, neither a dash
  await expect(row("2").locator("td").nth(3)).toHaveText("reader saw nothing");
  await expect(row("2").locator("td").nth(4)).toContainText("10");
  for (const cell of await table.locator("tbody tr td:nth-child(4), tbody tr td:nth-child(5)").allTextContents()) expect(cell.trim()).not.toBe("—");
  await shoot(page, "child-page-columns");
  await page.context().close();
  expect(ashaCapture).not.toBe("");
});
