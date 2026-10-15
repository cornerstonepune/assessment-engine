/**
 * U17 — Curriculum (goals/ui3-curriculum.yaml). Nimish, 2026-10-11: "When I go to the curriculum, it has grade-wise,
 * topic-wise descriptions, and people can open and look at the skills and the whole mapping of the curriculum. If there
 * are edits, some changes, tagging, etc., or definitions that need to be changed, one can do that." A skill's page in
 * five parts; a skill approved on its own; a topic switched on once the person has read what it does; the engine's
 * questions one line each until opened. Every change is put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U17-CLASS";
const CODE = /\bM_[A-Z0-9_]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("a skill's page is in five parts, its worksheets one level at a time, and no code on it", async ({ page }) => {
  await page.goto("/skill-sets/ADD.2D2D");
  const parts = page.getByRole("navigation", { name: "Parts of this skill" });
  await expect(parts.getByRole("link")).toHaveText(["What it means", "Levels", "Mistakes", "Questions", "Worksheets"]);
  await expect(parts.getByRole("link", { name: "Questions" })).toHaveAttribute("href", /^\/library\?set=ADD\.2D2D/);
  for (const [part, id] of [["Levels", "levels"], ["Mistakes", "mistakes"], ["Worksheets", "worksheets"]]) {
    await expect(parts.getByRole("link", { name: part })).toHaveAttribute("href", `#${id}`);
    await expect(page.locator(`#${id}`)).toBeVisible();
  }

  // the worksheets of one level at a time, the first, each named by its level and number
  const sheets = page.getByRole("table", { name: "Worksheets for this skill" });
  const levels = await sheets.locator("tbody tr td:nth-child(2)").allInnerTexts();
  expect(levels.length).toBeGreaterThan(0);
  expect(new Set(levels).size, "one level at a time").toBe(1);
  await expect(sheets.locator("tbody tr").first().locator("td").first()).toHaveText(/^(Easy|Medium|Hard|Advance) · sheet \d+/);
  expect(await page.getByRole("main").innerText(), "a mistake's code on the page").not.toMatch(CODE);
});

test("a skill is approved on its own, from skills grouped by grade", async ({ page }) => {
  const codes = ["ADD.2D2D", "SUB.2D2D"];
  const before = await sql<{ code: string; name: string; status: string; ratified_by: string | null; version: number }[]>`
    select code, name, status, ratified_by, version from skill_set where code = any(${codes}) order by code`;
  try {
    await sql`update skill_set set status = 'draft', ratified_by = null where code = any(${codes})`;
    await page.goto("/skill-sets/approve");
    // the grades are a choice at the top, each skill a row of the table (goals/ui6a-approve-filtered.yaml)
    await expect(page.getByRole("navigation", { name: "Grade" }).getByRole("link", { name: /^Grade 2/ })).toBeVisible();
    await page.locator('tr[data-row="ADD.2D2D"]').getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` }).click();
    // the page was at this address before the click: wait for what the approval itself brings back
    await expect(page).toHaveURL(/\/skill-sets\/approve\?approved=1$/);
    await expect(page.getByRole("status").filter({ hasText: "Approved, in your name." })).toBeVisible();
    const after = await sql<{ code: string; status: string; ratified_by: string | null }[]>`
      select code, status, ratified_by from skill_set where code = any(${codes}) order by code`;
    expect(after).toEqual([
      { code: "ADD.2D2D", status: "ratified", ratified_by: TEST_STAFF.name },
      { code: "SUB.2D2D", status: "draft", ratified_by: null },
    ]);

    // a skill changed by someone else after the page was opened is not approved, and the page says so
    await sql`update skill_set set version = version + 1 where code = 'SUB.2D2D'`;
    await page.locator('tr[data-row="SUB.2D2D"]').getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` }).click();
    await expect(page.getByRole("status").filter({ hasText: "Nothing was approved" })).toBeVisible();
    const [still] = await sql<{ status: string }[]>`select status from skill_set where code = 'SUB.2D2D'`;
    expect(still.status).toBe("draft");
  } finally {
    for (const s of before) {
      await sql`update skill_set set status = ${s.status}, ratified_by = ${s.ratified_by}, version = ${s.version} where code = ${s.code}`;
    }
  }
});

test("a topic is switched on only after the person has read what it does", async ({ page }) => {
  // said of one class, the test's own (goals/f1f-taught-per-class.yaml)
  await aClass(sql, CLASS, "G3", ["Ojas", "Pari"]);
  const [topic] = await sql<{ name: string; taught: boolean }[]>`select name, taught from topic where code = 'DIVCOL'`;
  expect(topic.taught, "division by a 1-digit number waits for an educator's word").toBe(false);
  try {
    await page.goto("/");
    const row = page.getByRole("region", { name: "Not taught yet", exact: true }).getByRole("listitem").filter({ hasText: topic.name });
    const confirm = row.getByRole("button", { name: `Taught in ${CLASS}, as ${TEST_STAFF.name}`, includeHidden: true });
    await expect(confirm).toHaveCount(1);
    await expect(confirm).toBeHidden();
    await row.getByText("Say it is taught", { exact: true }).click();
    await expect(row).toContainText("No other class changes");
    await confirm.click();
    await expect(page.getByRole("main")).toContainText(`${topic.name} is taught in ${CLASS} now`);
    const [now] = await sql<{ taught: boolean }[]>`select taught from class_topic where section = ${CLASS} and topic_code = 'DIVCOL'`;
    expect(now.taught).toBe(true);
  } finally {
    await sql`delete from class_topic where section = ${CLASS}`;
  }
});

test("each question the engine drafted is one line until it is opened", async ({ page }) => {
  const [{ open }] = await sql<{ open: number }[]>`select count(*)::int as open from ask where answer is null`;
  expect(open).toBeGreaterThan(1);
  await page.goto("/asks");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Questions to answer");
  const agree = page.getByRole("button", { name: `Agree as drafted, as ${TEST_STAFF.name}`, includeHidden: true });
  await expect(agree).toHaveCount(open);
  for (const b of await agree.all()) await expect(b).toBeHidden();
  const [first] = await sql<{ question: string }[]>`select question from ask where answer is null order by ord nulls last, code limit 1`;
  await page.getByText(first.question, { exact: true }).first().click();
  await expect(page.getByRole("region", { name: first.question, exact: true }).getByRole("button", { name: `Agree as drafted, as ${TEST_STAFF.name}` })).toBeVisible();
});

test("the question bank finds a question by its words, within the choices made", async ({ page }) => {
  // the bank's questions: generated, live, of a taught skill — the same rule the page's own query keeps
  const bank = sql`i.source = 'generated' and i.status = 'active' and exists (
    select 1 from skill_set s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught
    where s.tenant_id = i.tenant_id and s.code = i.skill_set_code)`;
  const [{ stem }] = await sql<{ stem: string }[]>`
    select i.stem from item i where ${bank} and i.stem ~ '[A-Za-z]{6,}' order by i.item_key limit 1`;
  const word = stem.match(/[A-Za-z]{6,}/)![0].toLowerCase();
  const [{ total }] = await sql<{ total: number }[]>`
    select count(*)::int as total from item i where ${bank} and (i.stem ilike ${`%${word}%`} or i.spec ->> 'text' ilike ${`%${word}%`})`;
  expect(total).toBeGreaterThan(0);

  await page.goto("/library");
  const find = page.getByRole("search", { name: "Find a question" });
  await find.getByRole("searchbox", { name: "Words or numbers in the question" }).fill(word.toUpperCase());
  await find.getByRole("button", { name: "Find", exact: true }).click();
  const found = page.getByRole("region", { name: "Questions", exact: true });
  await expect(found).toContainText(`of ${total.toLocaleString("en-IN")}`);
  const cells = await found.getByRole("table").locator("tbody tr td:first-child").allInnerTexts();
  expect(cells.length).toBe(Math.min(total, 50));
  for (const c of cells) expect(c.toLowerCase()).toContain(word);

  // a level chosen keeps the words; clearing the choices clears them too
  await found.getByRole("link", { name: "Easy", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`find=${word.toUpperCase()}.*difficulty=Easy|difficulty=Easy.*find=${word.toUpperCase()}`));
  await found.getByRole("link", { name: "Clear all choices" }).click();
  await expect(page.getByRole("searchbox", { name: "Words or numbers in the question" })).toHaveValue("");

  // what is typed is looked for as it is: a % finds only questions with a % in them
  const [{ pct }] = await sql<{ pct: number }[]>`
    select count(*)::int as pct from item i where ${bank} and (strpos(i.stem, '%') > 0 or strpos(coalesce(i.spec ->> 'text', ''), '%') > 0)`;
  await page.getByRole("searchbox", { name: "Words or numbers in the question" }).fill("%");
  await page.getByRole("button", { name: "Find", exact: true }).click();
  if (pct === 0) await expect(found).toContainText("No questions match");
  else await expect(found).toContainText(`of ${pct.toLocaleString("en-IN")}`);
});

test("every page says the tab it is under, above its title, and the menu marks that tab", async ({ page }) => {
  const [{ key }] = await sql<{ key: string }[]>`select item_key as key from item where source = 'generated' and status = 'active' order by item_key limit 1`;
  const pages: [string, string][] = [
    ["/", "Curriculum"], ["/skill-sets/approve", "Curriculum"], ["/skill-sets/ADD.2D2D", "Curriculum"], ["/library", "Curriculum"],
    [`/library/${key}`, "Curriculum"], ["/worksheets", "Curriculum"], ["/worksheets/taxonomy", "Curriculum"], ["/asks", "Curriculum"],
    ["/papers", "Assessments"], ["/papers/make", "Assessments"], ["/papers/approve", "Assessments"], ["/make", "Assessments"],
    ["/home", "Assessments"], ["/capture", "Assessments"], ["/growth", "Children"],
  ];
  for (const [path, tab] of pages) {
    await page.goto(path);
    await expect(page.getByTestId("stage"), path).toHaveText(new RegExp(`^${tab}\\b`));
    await expect(page.getByRole("navigation", { name: "Sections" }).locator("[aria-current=page]"), path).toHaveText(new RegExp(`^${tab}`));
  }
});

test("a class's papers are approved under Assessments, and Worksheets is the library alone", async ({ page }) => {
  // Worksheets: every question on a numbered worksheet, and nothing of a week
  await page.goto("/worksheets");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Worksheets");
  await expect(page.getByRole("heading", { name: "This week\u2019s papers" })).toHaveCount(0);
  await expect(page.getByRole("table", { name: "Each child's paper this week" })).toHaveCount(0);
  // a class's week, asked for at its old address, opens where it is approved now
  await page.goto("/worksheets?section=NO-SUCH&week=2026-W41&kind=practice");
  await expect(page).toHaveURL(/\/papers\/approve\?section=NO-SUCH&week=2026-W41&kind=practice/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Class papers to approve");
});
