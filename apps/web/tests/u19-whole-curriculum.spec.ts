/**
 * U19 — the whole curriculum (goals/c1-whole-curriculum.yaml). Nimish, 2026-10-11: "how is it the case that grade 2
 * does not have any multiplication or such, but grade 3 directly starts with multiplication, and that too directly
 * with two- or three-digit by one-digit?" Every grade lists each skill with a level in it, taught or not, with that
 * grade's levels only, and says which are not taught yet; a level Achal moves to another grade moves on the
 * Curriculum, in his name. Every change is put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const table = (page: import("@playwright/test").Page) => page.getByRole("table", { name: "The curriculum, grade by grade" });
const levels = async (row: import("@playwright/test").Locator) =>
  Object.fromEntries(
    await Promise.all(["Easy", "Medium", "Hard", "Advance"].map(async (d) => [d, (await row.locator(`td[data-level=${d}]`).innerText()).trim() !== "—"])),
  );

test.afterAll(async () => {
  await sql.end();
});

test("every grade shows each skill with a level in it, taught or not, and says which are not taught yet", async ({ page }) => {
  const [mulcol] = await sql<{ taught: boolean }[]>`select taught from skill_set where code = 'MUL.2D1D'`;
  expect(mulcol.taught, "column multiplication waits for an educator's word").toBe(false);
  await page.goto("/");
  await page.getByRole("button", { name: "Open everything" }).click();
  const t = table(page);

  // 1-digit × 1-digit is the facts, at Grade 2; 3-digit × 1-digit and 2-digit × 2-digit at Grade 4
  for (const id of ["G1/MUL.GROUPS", "G2/MUL.FACTS", "G2/MUL.MODELS", "G4/MUL.3D1D", "G4/MUL.2D2D"]) {
    await expect(t.locator(`tr[data-row="${id}"]`), id).toBeVisible();
  }
  // 2-digit × 1-digit is Grade 2's at Easy and Medium and Grade 3's at Hard and Advance: under both, each with its own
  const g2 = t.locator('tr[data-row="G2/MUL.2D1D"]');
  const g3 = t.locator('tr[data-row="G3/MUL.2D1D"]');
  expect(await levels(g2)).toEqual({ Easy: true, Medium: true, Hard: false, Advance: false });
  expect(await levels(g3)).toEqual({ Easy: false, Medium: false, Hard: true, Advance: true });

  // not switched on says so, on the skill and on its topic when none of the topic's skills in the grade is: multiples
  // and factors, taught in no class (goals/t1-topics-are-operations.yaml); a taught one does not
  await expect(g2).toContainText("not taught yet");
  await expect(t.locator('tr[data-row="G2/FACTORS"]')).toContainText("not taught yet");
  await expect(t.locator('tr[data-row="G2/ADD.2D2D"]')).not.toContainText("not taught yet");
});

test("a level moved to another grade moves on the Curriculum, in the name of who moved it", async ({ page }) => {
  const [before] = await sql<{ level_band: Record<string, string> }[]>`select level_band from skill_set where code = 'MUL.2D1D'`;
  try {
    await page.goto("/skill-sets/MUL.2D1D");
    const grades = page.getByRole("region", { name: "Which grade each level belongs to" });
    await grades.getByLabel("Hard").selectOption({ label: "Grade 2" });
    await grades.getByRole("button", { name: "Save the grades" }).click();
    await expect(page).toHaveURL(/grades=1/);
    await expect(grades).toContainText(`Last moved by ${TEST_STAFF.name}`);
    const [now] = await sql<{ level_band: Record<string, string>; level_band_by: string | null }[]>`
      select level_band, level_band_by from skill_set where code = 'MUL.2D1D'`;
    expect(now.level_band.Hard).toBeUndefined(); // Grade 2 is the skill's own grade
    expect(now.level_band_by).toBe(TEST_STAFF.name);

    await page.goto("/");
    await page.getByRole("button", { name: "Open everything" }).click();
    expect(await levels(table(page).locator('tr[data-row="G2/MUL.2D1D"]'))).toEqual({ Easy: true, Medium: true, Hard: true, Advance: false });
    expect(await levels(table(page).locator('tr[data-row="G3/MUL.2D1D"]'))).toEqual({ Easy: false, Medium: false, Hard: false, Advance: true });
  } finally {
    await sql`update skill_set set level_band = ${sql.json(before.level_band)}, level_band_by = null, level_band_at = null where code = 'MUL.2D1D'`;
  }
});
