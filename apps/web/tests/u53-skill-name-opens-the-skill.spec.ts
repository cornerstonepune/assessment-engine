/**
 * U53 — A skill's name opens the skill (goals/apr_skill_name_opens_the_skill.yaml). Nimish, 2026-10-23, on Approve the
 * skills: "shouldn't this page have a link that opens the skill in detail - coz the questions associated with each level of
 * difficulty and all needs to be down too. I can't click on any of these skills and deep dive in."
 *
 * A Maths draft and an English draft (the loader's own rows) are each opened by clicking their name on the approve list; the
 * skill page shows each level with its questions (a count and a link to the library for Maths, a sentence for English), and
 * the same two actions the list has. At 1440 px. Every status the test changes is put back.
 */
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SHOTS = process.env.APR_SHOTS;
const MATHS = "ADD.2D2D";
let english = { code: "", name: "" };
let before: { code: string; status: string; ratified_by: string | null }[] = [];

test.beforeAll(async () => {
  const [e] = await sql<{ code: string; name: string }[]>`
    select s.code, s.name from skill s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code and t.subject_code = 'ENG'
    where s.code like 'EN3.%' order by s.code limit 1`;
  english = e;
  before = await sql`select code, status, ratified_by from skill where code in (${MATHS}, ${english.code})`;
  await sql`update skill set status = 'draft', ratified_by = null where code in (${MATHS}, ${english.code})`;
});

test.afterAll(async () => {
  for (const b of before) await sql`update skill set status = ${b.status}, ratified_by = ${b.ratified_by} where code = ${b.code}`;
  await sql.end();
});

const row = (page: Page, code: string) => page.locator(`[data-row="${code}"]`);

async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

test("a Maths skill's name on the approve list opens it, with each level's questions and the two actions", async ({ page }) => {
  await page.goto("/skill-sets/approve");
  await shot(page, "approve-list");
  const [{ name }] = await sql<{ name: string }[]>`select name from skill where code = ${MATHS}`;
  const link = row(page, MATHS).getByRole("rowheader").getByRole("link", { name });
  await expect(link).toHaveAttribute("href", `/skill-sets/${MATHS}`);
  // the keyboard reaches it and opens it
  await link.focus();
  await expect(link).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${MATHS}$`));

  const levels = await sql<{ difficulty: string }[]>`select difficulty from skill_level where skill_code = ${MATHS}`;
  expect(levels.length).toBeGreaterThan(0);
  for (const { difficulty: d } of levels) {
    const card = page.getByRole("region", { name: d, exact: true });
    await expect(card).toBeVisible();
    // the count of that level's questions is a link to the library, filtered to this skill and level
    await expect(card.getByRole("link", { name: /\d+ questions/ })).toHaveAttribute("href", new RegExp(`/library\\?set=${MATHS}&difficulty=${d}`));
  }
  await expect(page.getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` })).toBeVisible();
  await expect(page.getByRole("link", { name: "Change the words first" })).toHaveAttribute("href", `/skill-sets/${MATHS}/edit`);
  await shot(page, "skill-maths");
});

test("an English skill's name opens it, and each level shows its sample questions", async ({ page }) => {
  await page.goto("/skill-sets/approve");
  const link = row(page, english.code).getByRole("rowheader").getByRole("link", { name: english.name });
  await link.click();
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${english.code}$`));

  const levels = await sql<{ difficulty: string }[]>`select difficulty from skill_level where skill_code = ${english.code}`;
  expect(levels.length).toBeGreaterThan(0);
  for (const { difficulty: d } of levels) {
    const card = page.getByRole("region", { name: d, exact: true });
    await expect(card).toBeVisible();
    // its sample questions, not a promise of questions later (goals/smp_skill_shows_its_samples.yaml)
    await expect(card.locator("li[data-sample]").first()).toBeVisible();
    await expect(card.getByRole("link", { name: /questions/ }), "no empty count for a skill with no bank").toHaveCount(0);
  }
  await expect(page.getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` })).toBeVisible();
  await expect(page.getByRole("link", { name: "Change the words first" })).toHaveAttribute("href", `/skill-sets/${english.code}/edit`);
  await shot(page, "skill-english");
});

test("on Curriculum, a skill in a table row opens its skill page", async ({ page }) => {
  await page.goto("/");
  // the grade, subject and topic rows are folded: open them all, then follow the skill
  for (let i = 0; i < 4; i++) {
    const closed = page.locator('table button[aria-expanded="false"]');
    if (!(await closed.count())) break;
    await closed.first().click();
  }
  const skill = page.locator(`a[href="/skill-sets/${MATHS}"]`).first();
  await expect(skill).toBeVisible();
  await skill.click();
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${MATHS}$`));
  await expect(page.getByRole("region", { name: "Easy", exact: true })).toBeVisible();
});
