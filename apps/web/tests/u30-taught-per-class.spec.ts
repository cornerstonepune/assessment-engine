/**
 * U30 — taught is said for each class (goals/f1f-taught-per-class.yaml, ADR 0073 D5). Nimish, 2026-10-14: "people who
 * are there for one thing like educator only see something that's relevant for their class and their students", and
 * "It's not very clear that here you switch on a certain thing, or you go to the skills and you approve".
 *
 * An educator says a class of theirs has been taught a topic, in their own name; no other class changes, and a form
 * changed by hand to another class is refused. Make papers offers a class only what it has been taught. On Curriculum,
 * "Taught" (a person's word about a class) and "Assessed" (children with a checked answer) are two words.
 *
 * Two Grade 2 classes of the test's own (tests/rows.ts), made once and kept; the educator and every class's word on a
 * topic this test said are taken away after.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";
import { signIn } from "./sign-in";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U30-MINE";
const OTHER = "U30-OTHER";
const TOPIC = "FACTORS"; // multiples and factors: not taught in the school's rows; the nth multiple is Grade 2's
const EDUCATOR = { email: "u30-educator@cornerstone.test", name: "U30 Educator", role: "educator", classes: [MINE] };
let topicName: string;

test.beforeAll(async () => {
  await aClass(sql, MINE, "G2", ["Ira", "Jai"]);
  await aClass(sql, OTHER, "G2", ["Kavya", "Laksh"]);
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([EDUCATOR])}
    where key = 'app.staff'`;
  [{ name: topicName }] = await sql<{ name: string }[]>`select name from topic where code = ${TOPIC}`;
});
test.afterAll(async () => {
  await sql`delete from class_skill where section in (${MINE}, ${OTHER})`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function signedIn(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await signIn(page, EDUCATOR.email);
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

// a class's word on the topic: said of every one of its skills alike (goals/t1-topics-are-operations.yaml)
const said = (section: string) =>
  sql<{ taught: boolean; taught_by: string }[]>`
    select bool_and(taught) as taught, min(taught_by) as taught_by from class_skill
    where section = ${section} and skill_set_code in (select code from skill_set where topic_code = ${TOPIC})
    having count(*) > 0`;

test("an educator says a topic is taught in their class, in their name, and no other class changes", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    await page.goto("/");
    const row = page.getByRole("region", { name: "Not taught yet", exact: true }).getByRole("listitem").filter({ hasText: topicName });
    await expect(row).toContainText(`Not taught yet in ${MINE}`);
    await expect(row, "an educator is offered only their own classes").not.toContainText(OTHER);
    await row.getByText("Say it is taught", { exact: true }).click();
    await row.getByRole("button", { name: `Taught in ${MINE}, as ${EDUCATOR.name}` }).click();
    await expect(page.getByRole("main")).toContainText(`${topicName} is taught in ${MINE} now`);
    expect(await said(MINE)).toEqual([{ taught: true, taught_by: EDUCATOR.name }]);
    expect(await said(OTHER), "no other class changes").toEqual([]);
    const [school] = await sql<{ taught: boolean }[]>`select bool_or(taught) as taught from skill_set where topic_code = ${TOPIC}`;
    expect(school.taught, "one class's word is not the school's switch").toBe(false);

    // the form changed by hand to a class that is not theirs: refused, and nothing is said of that class
    await page.goto("/");
    const taught = page.getByRole("region", { name: "Taught", exact: true });
    await taught.locator("summary").click();
    const off = taught
      .getByRole("listitem")
      .filter({ hasText: topicName })
      .getByRole("button", { name: `Not taught in ${MINE}, as ${EDUCATOR.name}` });
    await off.locator("xpath=ancestor::form").locator('input[name="class"]').evaluate((el, s) => ((el as HTMLInputElement).value = s), OTHER);
    await off.click();
    await expect(page).toHaveURL(/\/refused/);
    await expect(page.getByRole("main")).toContainText("not one of your classes");
    expect(await said(OTHER)).toEqual([]);
  } finally {
    await page.context().close();
    await sql`delete from class_skill where section in (${MINE}, ${OTHER})`;
  }
});

test("make papers says which skills a class has not been taught, and still offers them", async ({ page }) => {
  try {
    const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
    await sql`
      insert into class_skill (tenant_id, section, skill_set_code, taught, taught_by)
      values (${tenant}, ${MINE}, 'MUL.MODELS', true, 'U30 test')`;
    // since L7 an educator may choose any skill (ADR 0081, Nimish, 2026-10-16); the line says which one the class
    // has not been taught
    const models = async (cls: string) => {
      await page.goto(`/papers/make?class=${cls}&kind=assessment&way=same`);
      await page.getByLabel("Topic 1").selectOption("MUL");
      return page.getByLabel("Skill 1").locator('option[value="MUL.MODELS"]').textContent();
    };
    expect(await models(MINE), "taught in the class").not.toContain("not taught yet");
    expect(await models(OTHER), "not taught in the class, and still offered").toContain("not taught yet");
  } finally {
    await sql`delete from class_skill where section in (${MINE}, ${OTHER})`;
  }
});

test("curriculum says taught and assessed as two words", async ({ page }) => {
  await page.goto("/");
  const table = page.getByRole("table", { name: "The curriculum, grade by grade" });
  await expect(table.getByRole("columnheader", { name: "Assessed", exact: true })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Taught", exact: true }), "answers are not a person's word").toHaveCount(0);
  const note = page.getByRole("main");
  await expect(note).toContainText("Assessed is read from the answers");
  await expect(note).toContainText("Taught is what an educator said of their class");
});
