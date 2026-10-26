/**
 * U65 — More questions like a sample (goals/gen_from_a_sample.yaml). Nimish, 2026-10-26: "The capability to edit a
 * certain level in a skill by putting in the sample questions, and the ability for the system to then generate a
 * certain number of questions of that pattern."
 *
 * At 1440 px: on Maths ADD.2D2D, approved at every level, the educator types "47 + 38", in columns, asks for 5; code
 * makes 5 of that kind of sum, the page says so, and Medium waits for approval. A sum the level does not make is kept
 * as a sample and nothing is made. On an English skill, "Make more like this" says in words that it is not switched on
 * until its prompt is scored (rule 7): a browser test calls no model. Approvals are put back after; questions made stay
 * in the local copy's bank, as any refill's do.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CODE = "ADD.2D2D";
let kept: unknown;
let english: { code: string; level: string; ord: number; kind: string };
let keptEnglish: unknown;

test.beforeAll(async () => {
  [{ kept }] = await sql<{ kept: unknown }[]>`select level_approved as kept from skill where code = ${CODE}`;
  await sql`update skill set level_approved = (select jsonb_object_agg(x, jsonb_build_object('by', 'Achal', 'at', now()))
                                               from jsonb_object_keys(difficulty) x) where code = ${CODE}`;
  [english] = await sql<(typeof english)[]>`
    select skill_code as code, difficulty as level, ord, question_type as kind from english_sample_now
    where difficulty = 'Easy' and question_type = 'ENG.CHOOSE' and passage_code is null order by skill_code, ord limit 1`;
  [{ keptEnglish }] = await sql<{ keptEnglish: unknown }[]>`select level_approved as "keptEnglish" from skill where code = ${english.code}`;
});

test.afterAll(async () => {
  await sql`update skill set level_approved = ${sql.json(kept as never)} where code = ${CODE}`;
  await sql`update skill set level_approved = ${sql.json(keptEnglish as never)} where code = ${english.code}`;
  await sql.end();
});

test("an educator asks for more questions like a Maths sample and is told what was made, and an English one waits for its score", async ({ page }) => {
  const count = async () =>
    (await sql<{ n: number }[]>`select count(*)::int as n from item where skill_set_code = ${CODE} and difficulty = 'Medium'`)[0].n;
  const before = await count();
  await page.goto(`/skill-sets/${CODE}`);
  const more = page.locator('[data-more="Medium"]');
  await more.getByText("More questions like a sample").click();
  await more.getByLabel("A sample question at Medium").fill("47 + 38");
  await more.getByLabel("In columns").check();
  await more.getByLabel("How many").fill("5");
  await more.getByRole("button", { name: "Make questions like this" }).click();
  await expect(page.getByText("5 questions made like your sample")).toBeVisible();
  await expect(page.getByText("Medium waits for approval again, and no paper draws them before it is approved")).toBeVisible();
  expect(await count()).toBe(before + 5);

  // a sum Medium does not make: kept as a sample, nothing made
  const again = page.locator('[data-more="Medium"]');
  await again.getByText("More questions like a sample").click();
  await again.getByLabel("A sample question at Medium").fill("6 × 7");
  await again.getByRole("button", { name: "Make questions like this" }).click();
  await expect(page.getByText("Your sample is kept as a sample. It is not a kind of sum Medium makes")).toBeVisible();
  expect(await count()).toBe(before + 5);

  // English: written by a model, which is not switched on until its prompt is scored
  await page.goto(`/skill-sets/${english.code}`);
  const card = page.locator(`#level-${english.level} section[data-kind="${english.kind}"] li[data-sample="${english.ord}"]`);
  await card.getByText("Make more like this").click();
  await card.getByRole("button", { name: `Make questions like sample ${english.ord}` }).click();
  await expect(page.getByText("Making questions is not switched on yet")).toBeVisible();
});
