/**
 * U46 — One meaning per word (goals/ux8c-one-word.yaml). Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we
 * have right now for math, making sure that every screen and every other representation is thought through well: it's
 * clear, it's accurate, clickability is fine."
 *
 * A Grade 2 class of the test's own, made once and kept (evidence is append-only): Asha has signed-off answers and no
 * parent report, so the reports page lists her. The educator teaches the class. Each test reads a page as a person does
 * and checks that the same thing is said one way.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U46-MINE";
const EDUCATOR = { email: "u46-educator@cornerstone.test", name: "U46 Educator", role: "educator", classes: [SECTION] };
const PASSWORD = "u46-a-long-test-password";
const SALT = "46112233445566778899aabbccddeeff";
let kids: Record<string, string>;

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${kids.Asha}`;
  if (!n) {
    const [skill] = await sql<{ code: string; rung: string }[]>`
      select ss.registry_codes[1] as code, ss.rung_code as rung from skill ss
      where ss.code = 'ADD.2D2D'`;
    for (const right of [true, true, true, false]) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${kids.Asha}, ${skill.code}, ${skill.rung}, ${right}, '{}', 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${kids.Asha}::uuid)`;
  }
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const page = await (await browser.newContext({ storageState: { cookies: [], origins: [] } })).newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

test("Curriculum says taught one way: a grade's topic row is that grade's, and the one action has one name", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/");
  const table = page.getByRole("table", { name: "The curriculum, grade by grade" });
  // Multiplication is taught at Grade 1 (the panel above counts it taught); none of its Grade 2 skills is
  const row = table.locator('tr[data-row="G2/MUL"]');
  await expect(row).toContainText("not taught yet at this grade");
  await expect(row.getByRole("button", { name: `Say it is taught in ${SECTION}` })).toBeVisible();
  await expect(page.locator("main")).not.toContainText("Mark taught");
  await page.context().close();
});

test("the parent reports page says what it lists: reports not up to date, never 'waiting on a person' for one no one has written", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth/reports");
  const main = page.locator("main");
  await expect(main.getByRole("table", { name: "Parent reports not up to date" })).toContainText("Asha");
  await expect(main).not.toContainText(/waits? on a person/i);
  await page.context().close();
});

test("the question bank says what its total counts, beside Curriculum's", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/library");
  await expect(page.locator("main")).toContainText("ready, of the skills taught in your classes");
  await expect(page.locator("main")).toContainText("Curriculum counts every skill of the grade, taught or not");
  await page.context().close();
});

test("Today says what the reader can settle in an educator's words", async ({ browser }) => {
  const page = await asEducator(browser);
  const queue = page.getByRole("region", { name: "Is the queue shrinking?", exact: true });
  await expect(queue).toContainText("The reader settles a right answer by itself only on a kind of question it has earned trust on");
  await expect(queue).not.toContainText("the nearest");
  await page.context().close();
});

test("one word for one thing: a state by its own words, a skill as a skill, a count with its noun", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth");
  const main = page.locator("main");
  await expect(main).toContainText("Needs help on");
  await expect(main).not.toContainText(/red skill|amber one/);
  // a child's name is a link, and looks like every other link on the site: the same in the list of children who need the
  // educator and in the class's table. "Against every skill" is the quiet link under the table (goals/ux10-declutter.yaml).
  const names = main.getByRole("link", { name: "Asha", exact: true });
  const colour = (l: typeof names) => l.evaluate((el) => getComputedStyle(el).color);
  expect(await colour(names.first())).toBe(await colour(names.last()));
  await page.goto(`/growth?class=${SECTION}`);
  const against = page.locator("main").getByRole("link", { name: "Against every skill →" });
  expect(await colour(against), "the all-skills link is quieter than a name").not.toBe(await colour(names.last()));
  await page.goto(`/growth/${kids.Asha}/report`);
  await expect(page.locator("main")).toContainText("on this map assessed");
  await expect(page.locator("main")).not.toContainText(/skill sets?\b/);
  await page.goto("/worksheets/taxonomy");
  await expect(page.locator("main")).toContainText("cases on worksheets");
  await expect(page.locator("main")).not.toContainText(/\b1 (questions|worksheets)\b/);
  await page.context().close();
});
