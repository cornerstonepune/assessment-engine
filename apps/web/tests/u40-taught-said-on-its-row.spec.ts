/**
 * U40 — "not taught yet" is said where it shows (goals/l9-not-taught-is-said-where-it-shows.yaml). Nimish, 2026-10-16:
 * "while this is showing not taught; on the tip i am not even having an option to mark these as taught".
 *
 * Grade 2 classes of the test's own (tests/rows.ts). Multiplying three numbers and Multiples & factors are not taught
 * in the school's rows; the test takes back what it says. The coordinator sees every class, so a row offers a choice of
 * them; an educator with one class is offered that class alone, in one button.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U40-G2";
const OTHER = "U40-G2B";
const EDUCATOR = { email: "u40-educator@cornerstone.test", name: "U40 Educator", role: "educator", classes: [CLASS] };
const PASSWORD = "u40-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
const others = sql`(select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s where s ->> 'email' <> ${EDUCATOR.email})`;

test.beforeAll(async () => {
  await aClass(sql, CLASS, "G2", ["Om", "Pia"]);
  await aClass(sql, OTHER, "G2", ["Raj", "Sia"]);
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`update config set value = ${others} || ${sql.json([{ ...EDUCATOR, password }])} where key = 'app.staff'`;
});
test.afterEach(async () => {
  await sql`delete from class_skill where section in (${CLASS}, ${OTHER})`;
});
test.afterAll(async () => {
  await sql`update config set value = ${others} where key = 'app.staff'`;
  await sql.end();
});

async function educator(browser: Browser): Promise<Page> {
  const page = await (await browser.newContext({ storageState: { cookies: [], origins: [] } })).newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

const grade2 = async (page: Page) => {
  await page.goto("/");
  const table = page.getByRole("table", { name: "The curriculum, grade by grade" });
  // an educator's Curriculum opens on their grade already (goals/ux6-curriculum-for-the-educator.yaml); the coordinator's opens it
  const grade = table.getByRole("button", { name: "Grade 2", exact: true });
  if ((await grade.getAttribute("aria-expanded")) !== "true") await grade.click();
  await expect(grade).toHaveAttribute("aria-expanded", "true");
  return table;
};

test("a skill not taught yet is said taught from its own row, for one class", async ({ page }) => {
  const [{ name }] = await sql<{ name: string }[]>`select name from skill_set where code = 'MUL.THREE'`;
  const table = await grade2(page);
  await table.getByRole("button", { name: "Multiplication", exact: true }).click();
  const row = table.locator('tr[data-row="G2/MUL.THREE"]');
  await expect(row).toContainText("not taught yet");
  await row.getByLabel("Class").selectOption(CLASS);
  await row.getByRole("button", { name: "Mark taught" }).click();
  await expect(page.getByRole("main")).toContainText(`${name} is taught in ${CLASS} now`);
  const said = await sql<{ section: string; skill: string; taught: boolean }[]>`
    select section, skill_set_code as skill, taught from class_skill where section in (${CLASS}, ${OTHER})`;
  expect(said, "that one skill, for that one class").toEqual([{ section: CLASS, skill: "MUL.THREE", taught: true }]);
});

test("a topic not taught yet is said taught from its own row, every skill in it", async ({ browser }) => {
  const page = await educator(browser);
  const table = await grade2(page);
  const row = table.locator('tr[data-row="G2/FACTORS"]');
  await expect(row).toContainText("not taught yet");
  await row.getByRole("button", { name: `Mark taught in ${CLASS}` }).click();
  await expect(page.getByRole("main")).toContainText(`is taught in ${CLASS} now`);
  const said = await sql<{ skill: string }[]>`
    select skill_set_code as skill from class_skill where section = ${CLASS} and taught order by 1`;
  const every = await sql<{ code: string }[]>`select code from skill_set where topic_code = 'FACTORS' order by 1`;
  expect(said.map((r) => r.skill)).toEqual(every.map((r) => r.code));
  await page.context().close();
});
