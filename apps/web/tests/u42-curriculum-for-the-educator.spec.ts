/**
 * U42 — Curriculum, the question bank and the worksheets open on the educator's grade (goals/ux6-curriculum-for-the-
 * educator.yaml). Nimish, 2026-10-15: "Most of the pages just have a long list for no reason. All these things should
 * be expandable and collapsible. They should have the right set of columns which are important. It should be
 * teacher-specific."
 *
 * Two Grade 2 classes of the test's own, made once and kept (evidence is append-only): Asha in the educator's class and
 * Kavi in the other, each with checked answers on the same Grade 2 skill. The educator teaches the first only.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U42-MINE";
const OTHER = "U42-OTHER";
const EDUCATOR = { email: "u42-educator@cornerstone.test", name: "U42 Educator", role: "educator", classes: [MINE] };
const PASSWORD = "u42-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
// the class's grade, and a skill of it the test's children answered
let grade = { code: "", name: "" };
let skill = { code: "", rung: "" };

test.beforeAll(async () => {
  const mine = await aClass(sql, MINE, "G2", ["Asha"]);
  const other = await aClass(sql, OTHER, "G2", ["Kavi"]);
  [grade] = await sql<{ code: string; name: string }[]>`
    select g.code, g.name from grade g join child c on c.tenant_id = g.tenant_id and g.code = class_band(c.tenant_id, c.section)
    where c.id = ${mine.Asha}`;
  [skill] = await sql<{ code: string; rung: string }[]>`
    select s.skill_codes[1] as code, s.code as rung from rung s where s.band = ${grade.code} and cardinality(s.skill_codes) > 0
    and exists (select 1 from skill_set ss where ss.rung_code = s.code) order by s.ladder_order limit 1`;
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${mine.Asha}`;
  for (const id of [mine.Asha, other.Kavi]) {
    const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${id}`;
    if (n) continue;
    for (const right of [true, true, false]) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${id}, ${skill.code}, ${skill.rung}, ${right}, '{}', 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${id}::uuid)`;
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
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

const curriculum = (page: Page) => page.getByRole("table", { name: "The curriculum, grade by grade" });
const number = (s: string) => Number(s.replace(/[^\d]/g, "") || 0);

/** The questions an educator's class can be given of its own grade: generated, active, of a skill taught in the class,
 *  at a level whose row's grade is the class's. */
async function gradeQuestions(): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from item i
    join skill_level l on l.tenant_id = i.tenant_id and l.skill_code = i.skill_set_code and l.difficulty = i.difficulty
    where i.source = 'generated' and i.status = 'active' and l.grade = ${grade.code}
      and skill_taught_in(i.tenant_id, i.skill_set_code, ${MINE})`;
  return n;
}

test("Curriculum opens on the educator's grade, every other grade closed", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/");
  const rows = curriculum(page).locator('tbody tr[data-depth="0"]');
  await expect(rows.first()).toBeVisible();
  for (const row of await rows.all()) {
    const id = await row.getAttribute("data-row");
    await expect(row.getByRole("button"), `${id} is ${id === grade.code ? "open" : "closed"}`).toHaveAttribute(
      "aria-expanded",
      String(id === grade.code),
    );
  }
  // its topics show; no other grade's do
  await expect(curriculum(page).locator(`tbody tr[data-depth="2"][data-row^="${grade.code}/"]`).first()).toBeVisible();
  const topics = await curriculum(page).locator('tbody tr[data-depth="2"]').evaluateAll((trs) => trs.map((t) => t.getAttribute("data-row")));
  expect(topics.every((id) => id?.startsWith(`${grade.code}/`)), topics.join(", ")).toBe(true);
  await page.context().close();
});

test("Curriculum counts the children assessed in the educator's own class", async ({ browser, page }) => {
  const children = (p: Page) => curriculum(p).locator(`tbody tr[data-row="${grade.code}"] td`).nth(-2);
  const educator = await asEducator(browser);
  await educator.goto("/");
  await expect(children(educator), "Asha alone: Kavi is in another class").toHaveText("1");
  await educator.context().close();
  // the coordinator's count is every class's
  await page.goto("/");
  expect(number(await children(page).innerText())).toBeGreaterThanOrEqual(2);
});

test("the question bank opens on the educator's grade, every grade one tap away", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/library");
  const questions = page.getByRole("region", { name: "Questions" });
  const n = await gradeQuestions();
  expect(n).toBeGreaterThan(0);
  await expect(questions.locator(".panel-head")).toContainText(`of ${n.toLocaleString("en-IN")}`);
  await expect(questions.locator(".panel-head")).toContainText(grade.name);
  // every question listed is at a level of the class's grade
  const keys = await questions.locator("table tbody tr td:first-child a").evaluateAll((as) => as.map((a) => a.getAttribute("href")!.replace("/library/", "")));
  expect(keys.length).toBeGreaterThan(0);
  const off = await sql<{ item_key: string }[]>`
    select i.item_key from item i
    join skill_level l on l.tenant_id = i.tenant_id and l.skill_code = i.skill_set_code and l.difficulty = i.difficulty
    where i.item_key = any(${keys}) and l.grade <> ${grade.code}`;
  expect(off.map((r) => r.item_key), "a question of another grade").toEqual([]);
  await questions.getByRole("link", { name: "Every grade", exact: true }).click();
  await expect(questions.locator(".panel-head")).not.toContainText(grade.name);
  await page.context().close();
});

test("the bank's stock columns are every member of staff's, beside the educator's own grade's count", async ({ browser, page }) => {
  const { order } = { order: (await sql<{ code: string }[]>`select code from difficulty order by ord`).map((d) => d.code) };
  const educator = await asEducator(browser);
  await educator.goto("/library");
  // one role for now (goals/ux9c-one-role.yaml): the stock is theirs too, after their own grade's one count
  await expect(educator.getByRole("table", { name: "Questions by skill set and level" })).toHaveCount(1);
  const mine = educator.getByRole("table", { name: `${grade.name}: questions by skill` });
  await expect(mine.locator("thead th")).toHaveText(["Skill", "Kinds of question", "Questions"]);
  // one count per skill, the class's grade's; they add up to the list's
  const counts = await mine.locator("tbody tr td:last-child").allInnerTexts();
  expect(counts.reduce((a, c) => a + number(c), 0)).toBe(await gradeQuestions());
  await educator.context().close();
  // the coordinator keeps the stock: every grade, each level, the removed
  await page.goto("/library");
  const stock = page.getByRole("table", { name: "Questions by skill set and level" });
  await expect(stock.locator("thead th")).toHaveText(["Skill set", "Grade", "Kinds of question", ...order, "All"]);
  await expect(page.getByText(/\d removed/).first()).toBeVisible();
});

test("the worksheets open on the educator's grade, the counts and the list the same worksheets", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/worksheets");
  const library = page.locator("#library");
  const grid = library.getByRole("table", { name: "Worksheets by skill and level" });
  await expect(library.locator(".panel-head").first()).toContainText(grade.name);
  await expect(grid.locator("tbody tr").first()).toBeVisible();
  // the grid's counts add up to the pager's, and each worksheet listed is of the grade
  const cells = await grid.locator("tbody td.num a").allInnerTexts();
  const sum = cells.reduce((a, c) => a + number(c), 0);
  expect(sum).toBeGreaterThan(0);
  await expect(library.getByText(new RegExp(`of ${sum.toLocaleString("en-IN")}$`))).toBeVisible();
  const codes = await library.getByRole("table", { name: "Worksheets", exact: true }).locator("tbody tr td:first-child").allInnerTexts();
  const off = await sql<{ code: string }[]>`
    select code from sheet_template where source = 'library' and code = any(${codes}) and band <> ${grade.code}`;
  expect(off.map((r) => r.code), "a worksheet of another grade").toEqual([]);
  await library.getByRole("link", { name: "Every grade", exact: true }).click();
  await expect(library.locator(".panel-head").first()).not.toContainText(grade.name);
  await page.context().close();
});
