/**
 * U16 — Assessments (goals/ui2-assessments.yaml). Nimish, 2026-10-11: "for every child, there is a customized
 * assessment and the capability to create their own assessments or generate assessments as and when required for a
 * particular class. I can choose a class, I can choose the topic, and then it generates the default assessments for
 * that." Assessments opens on four ways to make one; a class and a topic fill the class's default assessment; every
 * paper's stage, class and week are words; an answer is checked and a paper signed off, one word each.
 *
 * The class, its worksheet and its read paper are the test's own (tests/rows.ts), made once and kept.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper, aWorksheet } from "./rows";
import { isoWeek, weekWords } from "../lib/week";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U16-TEST";
const WEEK = isoWeek();
const HELD = "the reader could not settle what was written";
let kids: Record<string, string> = {};

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const sums = ["46 + 38", "57 + 28"];
  const w = await aWorksheet(sql, {
    code: "U16-A", title: "U16 paper", date: "2026-10-10", band: "G2", week: WEEK,
    items: sums.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
  });
  await aReadPaper(sql, {
    qr: "U16TEST-1", child: kids.Asha, template: w.template, items: w.items,
    reads: [
      { status: "correct", read: "84" }, // marked by the engine, waiting to be signed off
      { status: "needs_teacher", read: "8?", why: HELD }, // waiting for a person to check
    ],
  });
});
test.afterAll(async () => {
  await sql.end();
});

test("Assessments opens on four ways to make one, each opening the maker ready for its use", async ({ page }) => {
  await page.goto("/papers");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Assessments");
  const make = page.getByRole("region", { name: "Make an assessment", exact: true });
  await expect(make.getByRole("link")).toHaveText([/^For a class/, /^For each child/, /^For one child/, /^A ready-made worksheet/]);

  // for a class: one assessment for every child, the class still to choose
  await make.getByRole("link", { name: /^For a class/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Make papers");
  await page.getByRole("form", { name: "Choose the papers" }).getByLabel("Class").selectOption({ value: SECTION });
  await page.getByRole("button", { name: "Show the class" }).click();
  await expect(page.getByRole("radio", { name: /Class assessment/ })).toBeChecked();
  await expect(page.getByRole("radio", { name: /One paper for all/ })).toBeChecked();
  for (const box of await page.getByRole("checkbox").all()) await expect(box).toBeChecked();

  // for one child: the same maker, no child ticked until the educator ticks one
  await page.goto("/papers");
  await make.getByRole("link", { name: /^For one child/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Make papers");
  await page.getByRole("form", { name: "Choose the papers" }).getByLabel("Class").selectOption({ value: SECTION });
  await page.getByRole("button", { name: "Show the class" }).click();
  await expect(page.getByRole("checkbox", { checked: true })).toHaveCount(0);

  // for each child: this week's home assessments, one per child from their record; a worksheet: the library
  await page.goto("/papers");
  await make.getByRole("link", { name: /^For each child/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Home assessments");
  await page.goto("/papers");
  await make.getByRole("link", { name: /^A ready-made worksheet/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Worksheets");
});

test("a class and a topic make the class's default assessment, every child's paper seen first", async ({ page }) => {
  // a topic with taught skills at Grade 2, and the class's default: its taught Grade 2 skills in the ladder's order,
  // each at Medium where it has one, else its first level (taught skill by skill: goals/t1-topics-are-operations.yaml)
  const [topic] = await sql<{ code: string; name: string }[]>`
    select t.code, t.name from topic t where exists (
      select 1 from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
      where s.topic_code = t.code and r.band = 'G2' and s.taught) order by t.ord limit 1`;
  expect(topic, "a taught topic with Grade 2 skills").toBeTruthy();
  const sets = await sql<{ code: string; difficulty: Record<string, string> }[]>`
    select s.code, s.difficulty from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    where s.topic_code = ${topic.code} and r.band = 'G2' and s.taught order by r.ladder_order nulls last, s.code limit 3`;
  const levels = ["Easy", "Medium", "Hard", "Advance"];
  const want = sets.map((s) => `${s.code}~${s.difficulty.Medium ? "Medium" : levels.find((d) => s.difficulty[d])}`);

  await page.goto(`/papers/make?kind=assessment&way=same`);
  await page.getByRole("form", { name: "Choose the papers" }).getByLabel("Class").selectOption({ value: SECTION });
  await page.getByRole("button", { name: "Show the class" }).click();
  await page.getByLabel("Topic").selectOption({ label: topic.name });
  await page.getByRole("button", { name: "See the papers" }).click();
  for (const [i, value] of want.entries()) await expect(page.getByLabel(`Skill and level ${i + 1}`)).toHaveValue(value);
  // nothing is made until the educator has seen each child's paper
  const papers = page.getByRole("region", { name: "The papers" });
  for (const name of ["Asha", "Bina"]) await expect(papers).toContainText(name);
  await expect(papers.getByRole("button", { name: /^Make and approve/ })).toBeVisible();
});

test("every assessment's stage, class and week are said in words", async ({ page }) => {
  await page.goto(`/papers?view=papers&class=${SECTION}`);
  const stages = page.getByRole("navigation", { name: "Papers by stage" });
  await expect(stages.getByRole("link")).toHaveText([/^Every stage/, /^To approve/, /^With the children/, /^To check/, /^To sign off/, /^Done/]);
  const table = page.getByRole("table", { name: "Every paper" });
  const row = table.locator("tbody tr").filter({ hasText: "U16 paper" });
  await expect(row.locator("td")).toHaveText(["U16 paper", "Earlier paper", `Grade 2 · ${SECTION}`, "Asha", weekWords(WEEK), "to check", "1", "—"]);
  expect(await table.innerText(), "an ISO week code in the list").not.toMatch(/\b\d{4}-W\d{2}\b/);
  await stages.getByRole("link", { name: /^To check/ }).click();
  await expect(page).toHaveURL(/stage=scanned/);
  await expect(table.locator("tbody tr").filter({ hasText: "U16 paper" })).toHaveCount(1);
});

test("an answer is checked and a paper signed off, one word for each", async ({ page }) => {
  await page.goto(`/growth/${kids.Asha}`);
  const main = page.getByRole("main");
  await expect(main.getByRole("region", { name: "Answers to check", exact: true })).toBeVisible();
  await expect(main.getByRole("button", { name: /^Sign off 1 answer as / })).toBeVisible();
  expect(await main.innerText(), "settle or confirm for an answer").not.toMatch(/\b(settle|Settled|confirm|Confirm)\b/);
});
