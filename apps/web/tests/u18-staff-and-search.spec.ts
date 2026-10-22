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
    await page.goto("/?taught=1");
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

// goals/ux10-declutter.yaml: Children had a second "find a child" box beside the bar at the top; the bar's search finds a
// child by name or roll without the name entering an address (s41-subject-class-and-today.spec.ts), so the page has one way.
test("Children has no second box to find a child: the bar at the top finds them", async ({ page }) => {
  await page.goto("/growth");
  await expect(page.getByRole("search", { name: "Subject, class and search" }).getByRole("searchbox")).toBeVisible();
  await expect(page.getByRole("searchbox", { name: "Find a child" })).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("searchbox")).toHaveCount(0);
});
