/**
 * U18 — the staff list and the search (goals/ui4a-staff-and-search.yaml). Nimish, 2026-10-11: "I think we'll have to
 * figure out a simpler login mechanism as well so that the decisions start getting logged in by them." An educator
 * put on the staff list as `engine staff add` puts them — email, name, role — signs in (by Google since
 * goals/a1-sign-in-with-google.yaml, tested there), and what they decide carries their name. Children finds a child as it is typed,
 * by name or roll, and the name never goes into the address (an address is logged; a name stays in pii).
 *
 * The class is the test's own (tests/rows.ts), made once and kept; the educator is taken off the list after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";
import { signIn } from "./sign-in";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U18-TEST";
const EDUCATOR = { email: "u18-educator@cornerstone.test", name: "U18 Educator", role: "educator", classes: [SECTION] };

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
  // on the list as `engine staff add` puts them
  await sql`update config set value = value || ${sql.json([EDUCATOR])} where key = 'app.staff'`;
  const [topic] = await sql<{ name: string; taught: boolean }[]>`select name, taught_in(tenant_id, code, null) as taught from topic where code = 'DIV'`;
  expect(topic.taught, "division waits for an educator's word").toBe(false);

  // a browser of the educator's own, signed in as them
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await signIn(page, EDUCATOR.email.toUpperCase());
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
  // the children's rows, class by class (the page's colour key is a table too); for the coordinator every class starts
  // closed (goals/ux3-children-grouped.yaml), so a row is on the page whether or not its class is open
  const rows = page.getByRole("table", { name: /: its children$/, includeHidden: true }).locator("tbody tr");
  await expect(find).toBeVisible();
  const all = await rows.count();
  expect(all).toBeGreaterThan(2);

  // part of a name, in any case: only the children whose name holds it, in every grade, their classes opened
  await find.fill("ZORA");
  const shown = rows.filter({ visible: true });
  await expect(shown).not.toHaveCount(all);
  for (const r of await shown.all()) await expect(r).toContainText(/zora/i);
  await expect(shown.filter({ hasText: "Zorawar" })).toHaveCount(1);
  expect(page.url(), "a child's name in the address").not.toMatch(/zora/i);
  // a grade with no child found is put away: only Grade 2 is left on the page
  await expect(page.locator("#children section").filter({ visible: true })).toHaveCount(1);
  await expect(page.getByRole("region", { name: "Grade 2" })).toBeVisible();

  // a number is a roll number: the children with that roll, class by class
  await find.fill("2");
  for (const r of await shown.all()) await expect(r.locator("td").first()).toHaveText("2");
  await expect(shown.filter({ hasText: "Mehrunissa" })).toHaveCount(1);

  // nothing found says so; clearing brings every child back and every class as it was, closed
  await find.fill("qqzzqq");
  await expect(shown).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "No child matches" })).toBeVisible();
  await find.fill("");
  await expect(page.locator("#children tr[data-name][hidden]")).toHaveCount(0);
  await expect(page.locator("#children details[data-class][open]")).toHaveCount(0);
});
