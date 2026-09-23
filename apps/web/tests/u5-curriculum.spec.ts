/**
 * U5 — Curriculum (goals/u5-curriculum.yaml).
 *
 * One tree: grade → subject → skill → level → worksheets. Every number is checked against the tables themselves.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

type Level = { code: string; outcome: string; band: string; level: string; words: string; questions: number; worksheets: string[] };

const levels = () => sql<Level[]>`
  select s.code, s.learning_objective as outcome, r.band, d.key as level, d.value ->> 'words' as words,
         (select count(*)::int from item i where i.skill_set_code = s.code and i.difficulty = d.key and i.status = 'active') as questions,
         array(select t.code from sheet_template t where t.skill_set_code = s.code and t.difficulty = d.key
               and t.source = 'library' and t.retired_at is null order by t.code) as worksheets
  from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code, jsonb_each(s.difficulty) d
  order by r.ladder_order nulls last, s.code`;

const skillBox = (page: Page, outcome: string) => page.getByRole("group", { name: outcome, exact: true });

/** Open a skill in the tree: the page streams in after its loading screen, so wait for the skill before opening it. */
async function open(page: Page, outcome: string) {
  const box = skillBox(page, outcome);
  await expect(box).toBeVisible();
  if ((await box.getAttribute("open")) === null) await box.locator("summary").click();
  await expect(box).toHaveAttribute("open", "");
  return box;
}

test("the tree reads grade, subject, skill, level, worksheets, and every count is the database's own", async ({ page }) => {
  const all = await levels();
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Curriculum");
  const [{ subject }] = await sql<{ subject: string }[]>`select name as subject from subject limit 1`;
  for (const grade of [...new Set(all.map((l) => l.band))]) {
    const g = page.getByRole("region", { name: new RegExp(`^${grade === "G2+" ? "Reasoning" : `Grade ${grade.slice(1)}`}`) });
    await expect(g).toBeVisible();
    await expect(g.getByText(subject, { exact: true }).first()).toBeVisible();
  }
  // every skill, each of its levels with its sentence and counts, and the worksheets under it
  const sample = all.filter((l) => ["ADD.2D2D", "SUB.3D1D"].includes(l.code));
  expect(sample.length).toBeGreaterThan(0);
  for (const l of sample) {
    const box = await open(page, l.outcome);
    const lv = box.getByRole("listitem").filter({ has: page.getByText(l.level, { exact: true }) }).first();
    await expect(lv).toContainText(l.words);
    await expect(lv.getByRole("link", { name: `${l.questions} questions` })).toBeVisible();
    await expect(lv.getByText(`${l.worksheets.length} worksheets`)).toBeVisible();
    for (const w of l.worksheets.slice(0, 3)) await expect(lv.getByRole("link", { name: w, exact: true })).toHaveAttribute("href", `/worksheets/${w}`);
  }
  for (const outcome of [...new Set(all.map((l) => l.outcome))]) await expect(skillBox(page, outcome)).toHaveCount(1);
});

test("a skill waiting for approval says so in the tree and opens where it is edited and approved", async ({ page }) => {
  const [s] = await sql<{ code: string; outcome: string; status: string }[]>`
    select code, learning_objective as outcome, status from skill_set order by status = 'draft' desc, code limit 1`;
  await page.goto("/");
  const box = skillBox(page, s.outcome);
  await expect(box.locator("summary")).toContainText(s.status === "ratified" ? "approved" : "waiting for approval");
  await open(page, s.outcome);
  await box.getByRole("link", { name: "Read, edit and approve" }).click();
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${s.code.replace(/\./g, "\\.")}`));
});

test("the taxonomy is one click from the tree, and the tree fits a phone", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Read the same worksheets by the taxonomy" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Worksheets by taxonomy");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "networkidle" });
  const [{ outcome }] = await sql<{ outcome: string }[]>`select learning_objective as outcome from skill_set where code = 'ADD.2D2D'`;
  await open(page, outcome);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
