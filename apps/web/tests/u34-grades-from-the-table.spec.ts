/**
 * U34 (B0b) — grades are read from the `grade` table (goals/b0b-grades-from-the-table.yaml, ADR 0085). The website listed
 * Grade 1 to 4 and "Reasoning · Grade 2 and up" in its code, and read a grade's number out of its code, so a Grade 10
 * level had nowhere to show and would have been read as Grade 1. Every change is put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const table = (page: import("@playwright/test").Page) => page.getByRole("table", { name: "The curriculum, grade by grade" });
const gradeRows = async (page: import("@playwright/test").Page) =>
  table(page).locator('tbody tr[data-depth="0"]').evaluateAll((rows) => rows.map((r) => r.getAttribute("data-row")));

test.afterAll(async () => {
  await sql.end();
});

test("a Grade 10 skill shows on the curriculum page, under Grade 10, after Grade 4", async ({ page }) => {
  const [before] = await sql<{ level_band: Record<string, string> }[]>`select level_band from skill_set where code = 'SUB.3D3D'`;
  try {
    // Achal moves a level to Grade 10 on the skill's own page: the grades offered are the table's
    await page.goto("/skill-sets/SUB.3D3D");
    const grades = page.getByRole("region", { name: "Which grade each level belongs to" });
    await grades.getByLabel("Advance").selectOption({ label: "Grade 10" });
    await grades.getByRole("button", { name: "Save the grades" }).click();
    await expect(page).toHaveURL(/grades=1/);
    const [now] = await sql<{ level_band: Record<string, string> }[]>`select level_band from skill_set where code = 'SUB.3D3D'`;
    expect(now.level_band.Advance).toBe("G10");

    await page.goto("/?details=1");
    await expect(table(page).getByRole("button", { name: "Grade 10", exact: true })).toBeVisible();
    const order = await gradeRows(page);
    expect(order.at(-1), "Grade 10 comes last, after Grade 4 — never sorted as text, between Grade 1 and Grade 2").toBe("G10");
    expect(order.indexOf("G10")).toBeGreaterThan(order.indexOf("G4"));
    await page.getByRole("button", { name: "Open everything" }).click();
    const row = table(page).locator('tr[data-row="G10/SUB.3D3D"]');
    await expect(row).toBeVisible();
    await expect(row.locator("td[data-level=Advance]")).not.toHaveText("—");
    await expect(row.locator("td[data-level=Easy]")).toHaveText("—");
    // read as its own grade, never as Grade 1
    await expect(table(page).locator('tr[data-row="G1/SUB.3D3D"]')).toHaveCount(0);
  } finally {
    await sql`update skill_set set level_band = ${sql.json(before.level_band)}, level_band_by = null, level_band_at = null where code = 'SUB.3D3D'`;
  }
});

test("reasoning sits under Grade 2, and no group is called Grade 2 and up", async ({ page }) => {
  await page.goto("/?details=1");
  await expect(table(page).getByRole("button", { name: "Grade 2", exact: true })).toBeVisible();
  await expect(table(page).getByText("Grade 2 and up")).toHaveCount(0);
  await page.getByRole("button", { name: "Open everything" }).click();
  for (const code of ["REASON.EXPLAIN", "REASON.FIND_MISTAKE"]) {
    await expect(table(page).locator(`tr[data-row="G2/${code}"]`), code).toBeVisible();
  }
});
