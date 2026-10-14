/**
 * U25 — each educator has classes (goals/f1a-each-educator-has-classes.yaml, ADR 0073 D1). Nimish, 2026-10-14: "Then the
 * teachers only see, when Achal logs in, things that are relevant to his grades." An educator on the staff list with the
 * classes they teach, as `engine staff add --class` puts them, signs in and the menu says those classes beside their
 * name: what the site is narrowed to is never a guess. The coordinator's are every class.
 *
 * The class is the test's own (tests/rows.ts), made once and kept; the educator is taken off the list after.
 */
import { scryptSync } from "node:crypto";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U25-TEST";
const EDUCATOR = { email: "u25-educator@cornerstone.test", name: "U25 Educator", role: "educator" };
const PASSWORD = "u25-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";

test.beforeAll(async () => {
  await aClass(sql, SECTION, "G2", ["Ishaan", "Tara"]);
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

test("an educator signs in and the menu says the classes they teach", async ({ browser }) => {
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`update config set value = value || ${sql.json([{ ...EDUCATOR, password, classes: [SECTION] }])} where key = 'app.staff'`;

  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await page.goto("/login");
    await page.getByLabel("School email").fill(EDUCATOR.email);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/today$/);
    const who = page.getByRole("complementary").getByRole("group", { name: "Signed in" });
    await expect(who).toContainText(EDUCATOR.name);
    await expect(who).toContainText(`Teaches ${SECTION}`);

    // a person with no class yet is told so, never shown an empty site in silence
    await sql`
      update config set value = (select jsonb_agg(case when s ->> 'email' = ${EDUCATOR.email}
                                                       then s || '{"classes": []}'::jsonb else s end)
                                 from jsonb_array_elements(value) s)
      where key = 'app.staff'`;
    await page.reload();
    await expect(who).toContainText("No class yet");
  } finally {
    await context.close();
  }
});

test("the coordinator's classes are every class", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByRole("complementary").getByRole("group", { name: "Signed in" })).toContainText("Every class");
});
