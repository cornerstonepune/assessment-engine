/**
 * U12 — Curriculum as one table (goals/u12-curriculum-table.yaml).
 *
 * Nimish, 2026-09-30: "I feel this should be like a proper table, and that table needs to have some kind of an
 * expand/collapse … When I click on grade 1, there is a proper table where, within grade 1, within mathematics, there
 * are addition and subtraction, and then within that, there is sub." And the columns: questions, worksheets, the
 * levels, "number of students which have been there", and "based on the assessments, whether that topic has been
 * taught or not".
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
test.afterAll(async () => sql.end());

const n = (x: number) => x.toLocaleString("en-IN");
const table = (page: Page) => page.getByRole("table", { name: "The curriculum, grade by grade" });
const depth = (page: Page, d: number) => table(page).locator(`tbody tr[data-depth="${d}"]`);

test("the curriculum is one table that opens grade by grade, topic by topic, and closes again", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("table")).toHaveCount(1);
  // at first, the grades only
  await expect(depth(page, 0).first()).toBeVisible();
  const grades = await depth(page, 0).count();
  expect(grades).toBeGreaterThan(0);
  await expect(table(page).locator("tbody tr")).toHaveCount(grades);

  // a grade opens its subject and its topics; its skills wait under their topics
  const grade = table(page).getByRole("button", { name: "Grade 2", exact: true });
  await grade.click();
  await expect(grade).toHaveAttribute("aria-expanded", "true");
  const [{ subject }] = await sql<{ subject: string }[]>`select name as subject from subject order by code limit 1`;
  await expect(table(page).locator('tr[data-row="G2/subject"]')).toContainText(subject);
  const topic = table(page).locator('tr[data-row="G2/ADDSUB"]');
  await expect(topic).toBeVisible();
  await expect(table(page).locator('tr[data-row="G2/ADD.2D2D"]')).toHaveCount(0);

  // a topic opens its skills, and closes them again
  await topic.getByRole("button").click();
  await expect(table(page).locator('tr[data-row="G2/ADD.2D2D"]')).toBeVisible();
  await topic.getByRole("button").click();
  await expect(table(page).locator('tr[data-row="G2/ADD.2D2D"]')).toHaveCount(0);

  // everything at once, and back to the grades
  await page.getByRole("button", { name: "Open everything" }).click();
  await expect(depth(page, 3).first()).toBeVisible();
  await page.getByRole("button", { name: "Close everything" }).click();
  await expect(table(page).locator("tbody tr")).toHaveCount(grades);
});

test("every row has the same columns, and every number is the database's own", async ({ page }) => {
  await page.goto("/");
  await expect(table(page).locator("thead th")).toHaveText([
    "Grade · subject · topic · skill",
    "Questions",
    "Worksheets",
    "Easy",
    "Medium",
    "Hard",
    "Advance",
    "Children assessed",
    "Taught",
  ]);
  await page.getByRole("button", { name: "Open everything" }).click();

  // one skill, at Grade 2's levels: its questions and worksheets, its children assessed, taught or not
  const levels = await sql<{ level: string; grade: string; questions: number; worksheets: number; words: string }[]>`
    select d.key as level, coalesce(s.level_band ->> d.key, r.band) as grade, d.value ->> 'words' as words,
           (select count(*)::int from item i where i.skill_set_code = s.code and i.difficulty = d.key and i.status = 'active') as questions,
           (select count(*)::int from sheet_template t where t.skill_set_code = s.code and t.difficulty = d.key
             and t.source = 'library' and t.retired_at is null) as worksheets
    from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code, jsonb_each(s.difficulty) d
    where s.code = 'ADD.2D2D'`;
  const g2 = levels.filter((l) => l.grade === "G2");
  const [{ kids }] = await sql<{ kids: number }[]>`
    select count(distinct s.child_id)::int as kids from child_skill_state s join child c on c.id = s.child_id and c.active
    join skill_set ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code where ss.code = 'ADD.2D2D' and s.n_events > 0`;
  const cells = table(page).locator('tr[data-row="G2/ADD.2D2D"] td');
  await expect(cells.nth(1)).toHaveText(n(g2.reduce((a, l) => a + l.questions, 0)));
  await expect(cells.nth(2)).toHaveText(n(g2.reduce((a, l) => a + l.worksheets, 0)));
  for (const [i, d] of ["Easy", "Medium", "Hard", "Advance"].entries()) {
    const l = g2.find((x) => x.level === d);
    await expect(cells.nth(3 + i)).toHaveText(l ? n(l.questions) : "—");
    if (l) await expect(cells.nth(3 + i)).toHaveAttribute("title", l.words);
  }
  await expect(cells.nth(7)).toHaveText(kids ? String(kids) : "—");
  await expect(cells.nth(8)).toHaveText(kids ? "yes" : "not yet");

  // a topic adds up its skills: questions, and how many of them are taught
  const skills = await sql<{ code: string; questions: number; taught: boolean }[]>`
    select s.code,
           (select count(*)::int from item i where i.skill_set_code = s.code and i.status = 'active'
             and coalesce(s.level_band ->> i.difficulty, r.band) = 'G2' and s.difficulty ? i.difficulty) as questions,
           exists (select 1 from child_skill_state k join child c on c.id = k.child_id and c.active
                   where k.rung_code = s.rung_code and k.n_events > 0) as taught
    from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught
    where s.topic_code = 'ADDSUB'
      and exists (select 1 from jsonb_object_keys(s.difficulty) d where coalesce(s.level_band ->> d, r.band) = 'G2')`;
  const topic = table(page).locator('tr[data-row="G2/ADDSUB"] td');
  await expect(topic.nth(1)).toHaveText(n(skills.reduce((a, s) => a + s.questions, 0)));
  await expect(topic.nth(8)).toHaveText(`${skills.filter((s) => s.taught).length} of ${skills.length}`);
});
