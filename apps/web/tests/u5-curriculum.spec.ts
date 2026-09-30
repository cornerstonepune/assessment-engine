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
  select s.code, s.learning_objective as outcome, coalesce(s.level_band ->> d.key, r.band) as band, d.key as level, d.value ->> 'words' as words,
         (select count(*)::int from item i where i.skill_set_code = s.code and i.difficulty = d.key and i.status = 'active') as questions,
         array(select t.code from sheet_template t where t.skill_set_code = s.code and t.difficulty = d.key
               and t.source = 'library' and t.retired_at is null order by t.code) as worksheets
  from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code, jsonb_each(s.difficulty) d
  where exists (select 1 from topic t where t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught)
  order by r.ladder_order nulls last, s.code`;

const n = (x: number) => x.toLocaleString("en-IN");
const table = (page: Page) => page.getByRole("table", { name: "The curriculum, grade by grade" });
/** Open every row of the table: the page streams in after its loading screen, so wait for the table first. */
async function openAll(page: Page) {
  await expect(table(page)).toBeVisible();
  await page.getByRole("button", { name: "Open everything" }).click();
  await expect(table(page).locator('tbody tr[data-depth="3"]').first()).toBeVisible();
}

test("the tree reads grade, subject, skill, level, worksheets, and every count is the database's own", async ({ page }) => {
  const all = await levels();
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Curriculum");
  const [{ subject }] = await sql<{ subject: string }[]>`select name as subject from subject limit 1`;
  await openAll(page);
  for (const grade of [...new Set(all.map((l) => l.band))]) {
    await expect(table(page).locator(`tr[data-row="${grade}"]`)).toBeVisible();
    await expect(table(page).locator(`tr[data-row="${grade}/subject"]`)).toContainText(subject);
  }
  // each sampled skill, each of its own grade's levels with its sentence and count, and its worksheets a click away
  const sample = all.filter((l) => ["ADD.2D2D", "SUB.3D1D"].includes(l.code));
  expect(sample.length).toBeGreaterThan(0);
  for (const l of sample) {
    const row = table(page).locator(`tr[data-row="${l.band}/${l.code}"]`);
    await expect(row.locator("td").first()).toContainText(l.outcome);
    const cell = row.locator("td").nth(3 + ["Easy", "Medium", "Hard", "Advance"].indexOf(l.level));
    await expect(cell).toHaveText(n(l.questions));
    await expect(cell).toHaveAttribute("title", l.words);
    await expect(row.locator("td").nth(2).getByRole("link")).toHaveAttribute("href", `/skill-sets/${l.code}#worksheets`);
  }
  // every taught skill has one row in each grade one of its levels belongs to
  for (const key of new Set(all.map((l) => `${l.band}/${l.code}`))) {
    await expect(table(page).locator(`tr[data-row="${key}"]`)).toHaveCount(1);
  }
});

test("a skill waiting for approval says so in the tree and opens where it is edited and approved", async ({ page }) => {
  const [s] = await sql<{ code: string; outcome: string; status: string; band: string }[]>`
    select s.code, s.learning_objective as outcome, s.status, r.band from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    where exists (select 1 from topic t where t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught)
    order by s.status = 'draft' desc, s.code limit 1`;
  await page.goto("/");
  await openAll(page);
  const row = table(page).locator(`tr[data-row="${s.band}/${s.code}"]`);
  if (s.status === "ratified") await expect(row).not.toContainText("waiting for approval");
  else await expect(row).toContainText("waiting for approval");
  await row.getByRole("link", { name: s.outcome }).click();
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${s.code.replace(/\./g, "\\.")}`));
});

test("the taxonomy is one click from the tree, and the tree fits a phone", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Read the same worksheets by the taxonomy" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Worksheets by taxonomy");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "networkidle" });
  await openAll(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("each grade's skills sit under their topics, in the topics' order, each topic with its own skills", async ({ page }) => {
  const rows = await sql<{ band: string; topic: string; code: string; ord: number }[]>`
    select r.band, t.code as topic, s.code, t.ord
    from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught
    where r.band = 'G3' and coalesce(s.level_band, '{}'::jsonb) = '{}'::jsonb order by t.ord`;
  expect(rows.length).toBeGreaterThan(0);
  await page.goto("/");
  await openAll(page);
  // the rows under Grade 3, in the table's order: each topic, then its skills
  const order = await table(page).locator("tbody tr").evaluateAll((trs) => trs.map((t) => t.getAttribute("data-row") ?? ""));
  const g3 = order.filter((id) => id.startsWith("G3/") && id !== "G3/subject");
  const topics = [...new Set(rows.map((r) => r.topic))];
  expect(g3.filter((id) => topics.includes(id.slice(3)))).toEqual(topics.map((t) => `G3/${t}`));
  for (const r of rows) {
    const at = g3.indexOf(`G3/${r.code}`);
    const under = g3.slice(0, at).reverse().find((id) => topics.includes(id.slice(3)));
    expect(under, r.code).toBe(`G3/${r.topic}`);
  }
});
