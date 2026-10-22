/**
 * E0 — English, Grades 3 and 4, in the system (goals/e0-english-in-the-system.yaml). Nimish, 2026-10-22: "Ayush is a part
 * of Cornerstone... This entire thing should fold within our system itself... he'll log into the system and all his
 * responses will be logged in properly."
 *
 * The rows are the loader's own (`engine load`), as drafts. An educator of the test's own signs in, reads one English skill
 * on the Curriculum page and its skill page, approves a level and one way of asking in their own name, and the record
 * keeps the name and the date. Everything the test approves is withdrawn afterwards, so English stays a draft.
 */
import { scryptSync } from "node:crypto";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const EDUCATOR = { email: "e0-educator@cornerstone.test", name: "E0 Educator", role: "educator", classes: [] as string[] };
const PASSWORD = "e0-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
const SHOTS = process.env.E0_SHOTS;

let skill = { code: "", name: "", objective: "", easy: "", open: "", mistake: "" };
let way = { code: "", words: "" };

test.beforeAll(async () => {
  // one English skill that is asked in a way a person checks every answer of, and names a mistake
  const [s] = await sql<{ code: string; name: string; learning_objective: string; easy: string; open: string; mistake: string }[]>`
    select s.code, s.name, s.learning_objective, l.looks_like as easy, q.words as open, m.name as mistake
    from skill_set s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code and t.subject_code = 'ENG'
    join skill_level l on l.tenant_id = s.tenant_id and l.skill_code = s.code and l.difficulty = 'Easy'
    join skill_level_question_type k on k.tenant_id = s.tenant_id and k.skill_code = s.code and k.question_type = 'ENG.SHORT_ANSWER'
    join question_type q on q.tenant_id = k.tenant_id and q.code = k.question_type
    join skill_mistake sm on sm.tenant_id = s.tenant_id and sm.skill_code = s.code
    join misconception m on m.tenant_id = sm.tenant_id and m.code = sm.misconception_code and m.op = sm.op
    where s.code like 'EN3.%' order by s.code, m.code limit 1`;
  skill = { code: s.code, name: s.name, objective: s.learning_objective, easy: s.easy, open: s.open, mistake: s.mistake };
  const [w] = await sql<{ code: string; words: string }[]>`
    select q.code, q.words from skill_level_question_type k join question_type q on q.tenant_id = k.tenant_id and q.code = k.question_type
    where k.skill_code = ${skill.code} and q.code = 'ENG.SHORT_ANSWER'`;
  way = w;
  await withdraw();
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});

/** English stays a draft: what a test approved is withdrawn. */
async function withdraw() {
  await sql`delete from question_type_approval where question_type = ${way.code}`;
  await sql`update skill_set set level_approved = '{}'::jsonb where code = ${skill.code}`;
}

test.afterAll(async () => {
  await withdraw();
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

async function shot(page: Page, name: string, fullPage = true) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage });
}

test("an educator reads an English skill's levels, kinds and mistakes and approves a level and a kind in their own name", async ({ browser }) => {
  const page = await asEducator(browser);
  // the Curriculum: English is a subject of its grade, its skill is a row with what each level asks
  await page.goto("/");
  await page.getByRole("button", { name: "Open everything" }).click();
  const english = page.locator('tr[data-row="G3/ENG"]');
  await expect(english).toContainText("English");
  const row = page.locator(`tr[data-row="G3/${skill.code}"]`);
  await expect(row).toContainText(skill.objective);
  await expect(row).toContainText(skill.easy);
  await row.scrollIntoViewIfNeeded();
  await shot(page, "1-curriculum", false);

  // the skill: each level in words, how it is asked (and that a person checks every written answer), its mistakes
  await row.getByRole("link", { name: skill.objective }).click();
  await expect(page.getByRole("heading", { level: 3, name: "Easy" })).toBeVisible();
  const levels = page.locator("#levels");
  await expect(levels).toContainText(skill.easy);
  await expect(levels).toContainText(`${way.words} · a person checks every answer`);
  const ways = page.getByRole("table", { name: "How it is asked" });
  await expect(ways.locator(`tr[data-way="${way.code}"]`)).toContainText("a person checks every answer");
  await expect(page.locator("#mistakes")).toContainText(skill.mistake);
  // the page's own words say nothing a bank would: no questions from a bank, no worksheets
  const text = (await page.locator("main").innerText()).toLowerCase();
  for (const jargon of ["taxonomy", "rung", "no question in the bank", "worksheets"]) expect(text, jargon).not.toContain(jargon);
  await shot(page, "2-skill");

  // approve one level: the record keeps the name and the date
  await page.locator('section[aria-label="Easy"]').getByRole("button", { name: "Approve Easy" }).click();
  await expect(page.locator('section[aria-label="Easy"]')).toContainText(`Approved · ${EDUCATOR.name}`);
  const [lv] = await sql<{ by: string | null; at: Date | null }[]>`
    select confirmed_by as by, confirmed_at as at from skill_level where skill_code = ${skill.code} and difficulty = 'Easy'`;
  expect(lv.by).toBe(EDUCATOR.name);
  expect(lv.at).not.toBeNull();

  // approve one way of asking: likewise
  await ways.locator(`tr[data-way="${way.code}"]`).getByRole("button", { name: `Approve “${way.words}”` }).click();
  await expect(page.getByText(`Approved “${way.words}”, in your name.`)).toBeVisible();
  await expect(ways.locator(`tr[data-way="${way.code}"]`)).toContainText(`Approved · ${EDUCATOR.name}`);
  const [a] = await sql<{ by: string; at: Date }[]>`select approved_by as by, approved_at as at from question_type_approval where question_type = ${way.code}`;
  expect(a.by).toBe(EDUCATOR.name);
  expect(Date.now() - a.at.getTime()).toBeLessThan(10 * 60_000);
  await shot(page, "3-approved");
  await page.context().close();
});

test("every member of staff is offered the approval", async ({ page, browser }) => {
  await withdraw(); // the first test approved them
  // the coordinator's session (the project's own)
  await page.goto(`/skill-sets/${skill.code}`);
  await expect(page.locator('section[aria-label="Easy"]').getByRole("button", { name: "Approve Easy" })).toBeVisible();
  await expect(page.getByRole("button", { name: `Approve “${way.words}”` })).toBeVisible();
  // and the educator's, who is not the coordinator
  const edu = await asEducator(browser);
  await edu.goto(`/skill-sets/${skill.code}`);
  await expect(edu.locator('section[aria-label="Easy"]').getByRole("button", { name: "Approve Easy" })).toBeVisible();
  await expect(edu.getByRole("button", { name: `Approve “${way.words}”` })).toBeVisible();
  await expect(edu.getByText("Waiting for the coordinator")).toHaveCount(0);
  await edu.context().close();
});
