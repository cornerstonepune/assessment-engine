/**
 * Step 12 — the worksheet library read by the team's taxonomy (goals/s12-worksheets-by-taxonomy.yaml).
 *
 * Which cases a question is, is the engine's (tests/test_taxonomy.py); this is what the team reads: each case,
 * where the rules set it, the worksheets that hold it, and each worksheet's own cases.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
test.afterAll(async () => {
  await sql.end();
});

test("the library reads case by case, each case with the worksheets that hold it", async ({ page }) => {
  await page.goto("/worksheets#library");
  await page.getByRole("link", { name: "See the worksheets by taxonomy case →" }).click();
  await expect(page.getByRole("heading", { name: "Worksheets by taxonomy" })).toBeVisible();

  const first = page.getByRole("table", { name: "Cases in §2.1" });
  const a01 = first.getByRole("row").filter({ hasText: "A01" });
  await expect(a01.getByText("on its level")).toBeVisible();
  await expect(a01.getByRole("link", { name: "1-digit + 1-digit" }).first()).toBeVisible();
  const [{ code }] = await sql<{ code: string }[]>`
    select min(t.code) as code from sheet_template t, unnest(t.item_ids) u(id) join item i on i.id = u.id
    where t.source = 'library' and t.retired_at is null and 'A01' = any(i.case_codes)`;
  const sheet = a01.getByRole("link", { name: code, exact: true });
  await expect(sheet).toBeVisible();
  await sheet.click();
  await expect(page.getByRole("heading", { name: `Worksheet ${code}` })).toBeVisible();

  // a pattern that questions at many levels show is named as that, not as a gap
  await page.goto("/worksheets/taxonomy");
  await page.getByRole("link", { name: "§5 Carry and exchange patterns" }).click();
  const p06 = page.getByRole("table", { name: "Cases in §5.1" }).getByRole("row").filter({ hasText: "P06" });
  await expect(p06.getByText("across levels")).toBeVisible();
});

test("a worksheet says which taxonomy cases it holds", async ({ page }) => {
  const [w] = await sql<{ code: string }[]>`
    select min(t.code) as code from sheet_template t, unnest(t.item_ids) u(id) join item i on i.id = u.id
    where t.source = 'library' and t.retired_at is null and 'S20' = any(i.case_codes)`;
  const held = await sql<{ code: string }[]>`
    select distinct x as code from sheet_template t, unnest(t.item_ids) u(id) join item i on i.id = u.id,
    unnest(i.case_codes) x where t.code = ${w.code} order by 1`;
  await page.goto(`/worksheets/${w.code}`);
  const list = page.getByRole("list", { name: "Taxonomy cases on this worksheet" });
  for (const c of held) await expect(list.getByRole("link", { name: c.code, exact: true })).toBeVisible();
  await expect(list.getByRole("listitem")).toHaveCount(held.length);
});

test("the taxonomy view fits a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/worksheets/taxonomy", "/worksheets/taxonomy?ch=5"]) {
    await page.goto(path, { waitUntil: "networkidle" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, path).toBeLessThanOrEqual(1);
  }
});
