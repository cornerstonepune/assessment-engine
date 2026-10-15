/**
 * U18 — the staff list and the search (goals/ui4a-staff-and-search.yaml). Nimish, 2026-10-11: "I think we'll have to
 * figure out a simpler login mechanism as well so that the decisions start getting logged in by them." An educator
 * put on the staff list as `engine staff add` puts them — email, name, role, the hash the sign-in checks — signs in
 * with their email and password, and what they decide carries their name. Children finds a child as it is typed,
 * by name or roll, and the name never goes into the address (an address is logged; a name stays in pii).
 *
 * The class is the test's own (tests/rows.ts), made once and kept; the educator is taken off the list after.
 */
import { scryptSync } from "node:crypto";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U18-TEST";
const EDUCATOR = { email: "u18-educator@cornerstone.test", name: "U18 Educator", role: "educator", classes: [SECTION] };
const PASSWORD = "u18-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";

test.beforeAll(async () => {
  await aClass(sql, SECTION, "G2", ["Zorawar", "Mehrunissa"]);
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

test("an educator put on the staff list signs in, and a decision carries their name", async ({ browser }) => {
  // on the list as `engine staff add` puts them: the hash is the one the sign-in checks (packages/engine/tests/test_cli.py)
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`update config set value = value || ${sql.json([{ ...EDUCATOR, password }])} where key = 'app.staff'`;
  const [topic] = await sql<{ name: string; taught: boolean }[]>`select name, taught_in(tenant_id, code, null) as taught from topic where code = 'DIV'`;
  expect(topic.taught, "division waits for an educator's word").toBe(false);

  // no session of the test's own: the educator signs in at the door like anyone
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await page.goto("/login");
    await page.getByLabel("School email").fill(EDUCATOR.email.toUpperCase());
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/today$/);

    // what they decide carries their name
    await page.goto("/");
    const row = page.getByRole("region", { name: "Not taught yet", exact: true }).getByRole("listitem").filter({ hasText: topic.name });
    await row.getByText("Say it is taught", { exact: true }).click();
    await row.getByRole("button", { name: `Taught in ${SECTION}, as ${EDUCATOR.name}` }).click();
    await expect(page.getByRole("main")).toContainText(`${topic.name} is taught in ${SECTION} now`);
    const [now] = await sql<{ taught: boolean; taught_by: string | null }[]>`
      select bool_and(taught) as taught, min(taught_by) as taught_by from class_skill where section = ${SECTION} and skill_set_code in (select code from skill_set where topic_code = 'DIV')`;
    expect(now).toEqual({ taught: true, taught_by: EDUCATOR.name });
  } finally {
    await context.close();
    await sql`delete from class_skill where section = ${SECTION}`;
  }
});

test("Children finds a child by name or roll as it is typed, and the name stays out of the address", async ({ page }) => {
  await page.goto("/growth");
  const find = page.getByRole("searchbox", { name: "Find a child" });
  // the children's rows, grade by grade (the page's colour key is a table too)
  const rows = page.getByRole("table", { name: /: every child$/ }).locator("tbody tr");
  await expect(rows.first()).toBeVisible();
  const all = await rows.count();
  expect(all).toBeGreaterThan(2);

  // part of a name, in any case: only the children whose name holds it, in every grade
  await find.fill("ZORA");
  const shown = rows.filter({ visible: true });
  await expect(shown).not.toHaveCount(all);
  for (const r of await shown.all()) await expect(r).toContainText(/zora/i);
  await expect(shown.filter({ hasText: "Zorawar" })).toHaveCount(1);
  expect(page.url(), "a child's name in the address").not.toMatch(/zora/i);
  // a grade with no child found is put away: only Grade 2's table is left on the page
  await expect(page.getByRole("table", { name: /: every child$/ }).filter({ visible: true })).toHaveCount(1);
  await expect(page.getByRole("table", { name: "Grade 2: every child" })).toBeVisible();

  // a number is a roll number: the children with that roll, class by class
  await find.fill("2");
  for (const r of await shown.all()) await expect(r.locator("td").first()).toHaveText("2");
  await expect(shown.filter({ hasText: "Mehrunissa" })).toHaveCount(1);

  // nothing found says so; clearing brings every child back
  await find.fill("qqzzqq");
  await expect(shown).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "No child matches" })).toBeVisible();
  await find.fill("");
  await expect(rows.filter({ visible: true })).toHaveCount(all);
});
