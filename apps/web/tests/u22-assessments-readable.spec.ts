/**
 * U22 — Assessments, readable (goals/ui5-assessments-readable.yaml). Nimish, 2026-10-11: "the assessment page needs to
 * have the filter and the view by topic and all. This cannot be just such a freaking long list of stuff. Need to make
 * it more readable." Assessments opens on one row for each assessment, its copies counted by stage; a topic keeps the
 * assessments on its skills; an assessment's row opens its copies, and every paper on its own is one click away.
 *
 * The class and its papers are the test's own (tests/rows.ts), made once and kept: a class assessment on 2-digit +
 * 2-digit given to three children — one read and waiting to be checked, one printed, one still to approve — and a
 * class practice on tally marks for one of them.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek, weekWords } from "../lib/week";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U22-TEST";
const WEEK = isoWeek();
let kids: Record<string, string> = {};
const setName = async (code: string) => (await sql<{ name: string }[]>`select name from skill where code = ${code}`)[0].name;

/** A paper made for one skill set at one level, its questions the bank's own; → its template and questions. */
async function aSheet(code: string, level: string): Promise<{ template: string; items: string[] }> {
  const [had] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where skill_set_code = ${code} and difficulty = ${level} and week = ${WEEK}
      and key ->> 'test' = 'u22'`;
  if (had) return { template: had.id, items: had.item_ids };
  const items = (await sql<{ id: string }[]>`
    select id from item where skill_set_code = ${code} and difficulty = ${level} and status is distinct from 'retired'
    order by id limit 2`).map((i) => i.id);
  const [{ id }] = await sql<{ id: string }[]>`
    insert into sheet_template (tenant_id, band, week, item_ids, skill_set_code, difficulty, key)
    select id, 'G2', ${WEEK}, ${items}::uuid[], ${code}, ${level}, '{"test": "u22"}' from tenant limit 1 returning id`;
  return { template: id, items };
}

/** One child's copy of a paper, of a kind, at a print status — a printed one approved by a person; made once. */
async function aCopy(qr: string, child: string, template: string, kind: string, status: string) {
  const by = status === "printed" ? "e2e" : null;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by)
    select tenant_id, ${qr}, ${template}, ${child}, ${WEEK}, ${SECTION}, ${kind}, ${status}, ${by} from child where id = ${child}
    on conflict do nothing`;
}

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan"]);
  const add = await aSheet("ADD.2D2D", "Medium");
  const tally = await aSheet("DATA.TALLY", "Easy");
  // Asha's copy is read: one answer marked, one the reader held for a person
  await aReadPaper(sql, {
    qr: "U22TEST-A",
    child: kids.Asha,
    template: add.template,
    items: add.items,
    reads: [{ status: "correct", read: "84" }, { status: "needs_teacher", read: "8?", why: "the reader could not settle it" }],
  });
  await sql`update sheet_instance set kind = 'assessment', week = ${WEEK}, section = ${SECTION}, print_status = 'returned'
            where qr_code = 'U22TEST-A'`;
  await aCopy("U22TEST-B", kids.Bina, add.template, "assessment", "printed");
  await aCopy("U22TEST-C", kids.Chetan, add.template, "assessment", "new");
  await aCopy("U22TEST-D", kids.Asha, tally.template, "practice", "new");
});
test.afterAll(async () => {
  await sql.end();
});

// each week's assessments are a table of their own (goals/ux5-papers-grouped.yaml); a line for each
const assessments = (page: Page) => page.getByRole("region", { name: "Papers" });
const ours = (page: Page) => assessments(page).locator("tr[data-assessment]").filter({ hasText: SECTION });

test("Assessments opens on one row for each assessment, its copies counted by stage", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}`);
  // the week is the group the assessments sit in, said once on its line
  await expect(page.getByRole("table", { name: `${weekWords(WEEK)}: its assessments` }).locator("thead th")).toHaveText([
    "Assessment",
    "Kind",
    "Class",
    "Copies",
    "Where they stand",
    "Waiting",
    "Score",
  ]);
  // three copies of one class assessment are one row, the tally practice another
  await expect(ours(page)).toHaveCount(2);
  const add = ours(page).filter({ hasText: await setName("ADD.2D2D") });
  await expect(add.locator("td")).toHaveText([
    await setName("ADD.2D2D"),
    "Class assessment",
    `Grade 2 · ${SECTION}`,
    "3",
    /1 to approve[^]*1 with the children[^]*1 to check/,
    "1",
    "—",
  ]);
  // a stage keeps the copies at that stage
  await page.getByRole("navigation", { name: "Papers by stage" }).getByRole("link", { name: /^To approve/ }).click();
  await expect(page).toHaveURL(/stage=made/);
  await expect(ours(page)).toHaveCount(2);
  await expect(ours(page).filter({ hasText: await setName("ADD.2D2D") }).locator("td").nth(3)).toHaveText("1");
  // in the school's words: no skill code, no ISO week
  expect(await assessments(page).innerText()).not.toMatch(/\b(\d{4}-W\d{2}|[A-Z]{3,}\.[A-Z0-9]+)\b/);
});

test("a topic keeps the assessments on its skills, and an assessment opens its copies", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}`);
  const topics = page.getByRole("navigation", { name: "Topic" });
  await expect(topics.getByRole("link", { name: "All topics" })).toHaveAttribute("aria-current", "page");
  await topics.getByRole("link", { name: "Data handling", exact: true }).click();
  await expect(page).toHaveURL(/topic=DATA\b/);
  await expect(ours(page)).toHaveCount(1);
  await expect(ours(page)).toContainText(await setName("DATA.TALLY"));
  // a topic stays chosen when the class changes, and the class when the topic does
  await page.getByRole("navigation", { name: "Topic" }).getByRole("link", { name: "Addition & subtraction", exact: true }).click();
  // the new topic's own row, waited for: the class was in the address before the click, so waiting on it alone let a
  // slow run click Data handling's row, whose one copy then failed the count (CI, 2026-10-12)
  await expect(page).toHaveURL(/topic=ADDSUB\b/);
  await expect(page).toHaveURL(new RegExp(`class=${SECTION}`));
  await expect(ours(page)).toHaveCount(1);
  await expect(ours(page)).toContainText(await setName("ADD.2D2D"));

  // the assessment, alone under these filters, is open on its copies, one row each, in roll order
  // (goals/ux5-papers-grouped.yaml)
  const papers = page.getByRole("table", { name: `${await setName("ADD.2D2D")}: each copy` });
  await expect(papers.locator("tbody tr")).toHaveCount(3);
  expect(await papers.locator("tbody tr td:nth-child(2)").allInnerTexts()).toEqual(["Asha", "Bina", "Chetan"]);
  // and it closes, and opens again, in place
  await ours(page).getByRole("link").first().click();
  await expect(page).toHaveURL(/[?&]open=none\b/);
  await expect(papers).toHaveCount(0);
  await ours(page).getByRole("link").first().click();
  await expect(papers.locator("tbody tr")).toHaveCount(3);
});
