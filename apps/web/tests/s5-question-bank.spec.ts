/**
 * Step 5 — the Question bank explains itself (goals/s5-question-bank-explained.yaml).
 *
 * Nimish, 2026-09-21: "I don't even know what the question bank is about, how it looks, and what kind
 * of mapping you have already done there." The page says what it is, and every question shows its ties.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

test("the bank says in plain words what it is, with the database's own numbers", async ({ page }) => {
  const [{ active, skills }] = await sql<{ active: number; skills: number }[]>`
    select (select count(*)::int from item where status = 'active' and source = 'generated') as active,
           (select count(*)::int from skill_set) as skills`;
  await page.goto("/library");
  const about = page.getByRole("region", { name: "What the bank is" }).or(page.locator("section.panel", { hasText: "What the bank is" }));
  await expect(about.first()).toContainText(`${active.toLocaleString("en-IN")} today, for the ${skills} skills`);
  await expect(about.first()).toContainText("a computer checks every answer");
  await expect(about.first()).toContainText("sits on at least one numbered worksheet");
});

test("every question shows its skill, level, kind and worksheets, and every link on the page opens", async ({ page }) => {
  await page.goto("/library");
  const rows = page.locator("#questions table tbody tr");
  await expect(rows.first()).toBeVisible();
  for (const row of (await rows.all()).slice(0, 20)) {
    await expect(row.locator("td").first().locator(".note")).toContainText(/Easy|Medium|Hard|Advance/);
    await expect(row.locator("td").nth(2)).not.toBeEmpty();
    await expect(row.locator("td").nth(3).getByRole("link").first()).toHaveAttribute("href", /^\/worksheets\/[RMX]\d{1,2}-[EMHA]\d{2,3}$/);
  }
  const hrefs = await page
    .getByRole("main")
    .locator("a[href]")
    .evaluateAll((as) => [...new Set(as.map((a) => (a as HTMLAnchorElement).getAttribute("href")!.split("#")[0]))]);
  expect(hrefs.length).toBeGreaterThan(50);
  for (const href of hrefs) {
    const res = await page.request.get(href);
    expect(res.status(), href).toBe(200);
  }
});

test("a question's worksheet opens and holds that question", async ({ page }) => {
  await page.goto("/library");
  const row = page.locator("#questions table tbody tr").first();
  const key = (await row.locator("td").first().getByRole("link").getAttribute("href"))!.replace("/library/", "");
  await row.locator("td").nth(3).getByRole("link").first().click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^Worksheet [RMX]\d{1,2}-[EMHA]\d{2,3}$/);
  await expect(page.locator(`a[href="/library/${key}"]`)).toBeVisible();
});
