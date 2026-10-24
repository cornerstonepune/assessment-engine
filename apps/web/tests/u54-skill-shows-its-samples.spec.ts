/**
 * U54 — A skill shows its sample questions (goals/smp_skill_shows_its_samples.yaml). Nimish, 2026-10-23, on an English
 * Grade 3 skill's page: "The skill description does not have the example questions or test questions for that level and
 * skill. It's just showing the difficulty levels and what the description of difficulty levels means. I was looking to
 * have the questions also there. How will the educator approve without having sample questions?"
 *
 * The rows are the loader's own (`engine load` fills `english_sample` from supabase/seed/english/). At 1440 px, from
 * Approve the skills: an English draft opened by its name shows, under each level, its samples grouped by kind, three of
 * each, with the right answer and each likely wrong answer's mistake in words; a kind a person reads says so and shows its
 * rubric; the approval sits under the samples. A skill with no samples says so in words. Everything changed is put back.
 */
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SHOTS = process.env.SMP_SHOTS;

type Sample = { difficulty: string; kind: string; ord: number; open: boolean; answer: unknown; wrong: { answer: string; mistake: string }[] };
let skill = { code: "", name: "", status: "", ratified_by: null as string | null };
let samples: Sample[] = [];

test.beforeAll(async () => {
  // an English Grade 3 skill asked both in a way code checks and in a way a person reads, with a rubric
  const [s] = await sql<{ code: string; name: string; status: string; ratified_by: string | null }[]>`
    select s.code, s.name, s.status, s.ratified_by from skill s
    where s.code like 'EN3.%'
      and exists (select 1 from english_sample e where e.skill_code = s.code and e.rubric_code is not null)
      and exists (select 1 from english_sample e join english_sample_wrong w on w.sample_id = e.id
                  where e.skill_code = s.code and e.question_type = 'ENG.CHOOSE')
    order by s.code limit 1`;
  skill = s;
  samples = await sql<Sample[]>`
    select e.difficulty, e.question_type as kind, e.ord, 'open_response' = any(q.marked) as open, e.answer,
           coalesce((select json_agg(json_build_object('answer', w.answer, 'mistake', m.name)) from english_sample_wrong w
                     join misconception m on m.tenant_id = w.tenant_id and m.code = w.mistake_code and m.op = w.op
                     where w.sample_id = e.id), '[]') as wrong
    from english_sample e join question_type q on q.tenant_id = e.tenant_id and q.code = e.question_type
    where e.skill_code = ${skill.code}`;
  await sql`update skill set status = 'draft', ratified_by = null where code = ${skill.code}`;
});

test.afterAll(async () => {
  await sql`update skill set status = ${skill.status}, ratified_by = ${skill.ratified_by} where code = ${skill.code}`;
  await sql.end();
});

async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

test("an English skill opened from Approve the skills shows each level's samples by kind, with the right answer and named mistakes", async ({ page }) => {
  await page.goto("/skill-sets/approve");
  await page.locator(`[data-row="${skill.code}"]`).getByRole("rowheader").getByRole("link", { name: skill.name }).click();
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${skill.code}$`));

  const levels = [...new Set(samples.map((s) => s.difficulty))];
  expect(levels.length).toBeGreaterThan(0);
  for (const d of levels) {
    const card = page.getByRole("region", { name: d, exact: true });
    const kinds = [...new Set(samples.filter((s) => s.difficulty === d).map((s) => s.kind))];
    for (const k of kinds) {
      const kind = card.locator(`section[data-kind="${k}"]`);
      await expect(kind.locator("li[data-sample]"), `${d} ${k}`).toHaveCount(3);
      for (const s of samples.filter((x) => x.difficulty === d && x.kind === k)) {
        const one = kind.locator(`li[data-sample="${s.ord}"]`);
        await expect(one.getByLabel("The right answer")).toBeVisible();
        if (typeof s.answer === "string") await expect(one.getByLabel("The right answer")).toContainText(s.answer);
        for (const w of s.wrong) await expect(one.getByLabel("Likely wrong answers")).toContainText(`${w.answer} · ${w.mistake}`);
      }
    }
    // the level's approval sits under its samples
    const approve = card.getByRole("button", { name: `Approve ${d}` });
    await expect(approve).toBeVisible();
    const lastSample = card.locator("li[data-sample]").last();
    expect((await approve.boundingBox())!.y).toBeGreaterThan((await lastSample.boundingBox())!.y);
  }
  // the skill's own approval and the link that changes its words (U55: it says what it changes) sit under the samples too, once
  const decide = page.locator("#levels #decide");
  await expect(decide.getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` })).toBeVisible();
  await expect(page.getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` })).toHaveCount(1);
  await expect(decide.getByRole("link", { name: "Change the description and each level’s sentence" })).toHaveAttribute("href", `/skill-sets/${skill.code}/edit`);
  await shot(page, "skill-samples");
});

test("a kind a person reads says so, and shows what a person reads the answer against", async ({ page }) => {
  await page.goto(`/skill-sets/${skill.code}`);
  const open = samples.find((s) => s.open)!;
  const kind = page.getByRole("region", { name: open.difficulty, exact: true }).locator(`section[data-kind="${open.kind}"]`);
  await expect(kind).toContainText("a person reads every answer");
  await kind.getByText("What a person reads the answer against:").click();
  const [r] = await sql<{ name: string; criterion: string }[]>`
    select r.name, r.criteria -> 0 ->> 'name' as criterion from english_sample e join rubric r on r.tenant_id = e.tenant_id
    and r.code = e.rubric_code where e.skill_code = ${skill.code} and e.difficulty = ${open.difficulty}
    and e.question_type = ${open.kind} limit 1`;
  await expect(kind).toContainText(r.name);
  await expect(kind).toContainText(r.criterion);
});

test("a skill with no sample questions says so in words", async ({ page }) => {
  const rows = await sql`select * from english_sample where skill_code = ${skill.code}`;
  const wrong = await sql`select w.* from english_sample_wrong w join english_sample e on e.id = w.sample_id where e.skill_code = ${skill.code}`;
  await sql`delete from english_sample where skill_code = ${skill.code}`;
  try {
    await page.goto(`/skill-sets/${skill.code}`);
    const d = samples[0].difficulty;
    await expect(page.getByRole("region", { name: d, exact: true })).toContainText("No sample questions yet.");
    await expect(page.locator("li[data-sample]")).toHaveCount(0);
  } finally {
    await sql`insert into english_sample select * from jsonb_populate_recordset(null::english_sample, ${sql.json(rows)})`;
    await sql`insert into english_sample_wrong select * from jsonb_populate_recordset(null::english_sample_wrong, ${sql.json(wrong)})`;
  }
});
