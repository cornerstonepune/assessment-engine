/**
 * U52 — Teaching is a page of its own (once Taught this week) (goals/uxn2-taught-this-week.yaml). Nimish, 2026-10-22: "make it easy to
 * navigate", the menu "in the order of the educator's week". Wednesday's step, saying what was taught, was the top of
 * the Curriculum page. It is now its own page, with the one main action and the week's next step; Today's line opens it,
 * and Curriculum links to it instead of carrying it.
 */
import { expect, test } from "@playwright/test";

test("Teaching is its own page: a table of topics, a tab for each subject, and the week's next step", async ({ page }) => {
  await page.goto("/taught");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Teaching");
  expect((await page.getByRole("navigation", { name: "Subjects" }).getByRole("link").allInnerTexts()).sort()).toEqual(["English", "Maths"]);
  await expect(page.locator("[data-ux=next]")).toHaveAttribute("href", "/papers");
  const rows = page.locator("tr[data-topic]");
  expect(await rows.count()).toBeGreaterThan(0);
  for (const row of await rows.all()) await expect(row.locator("[data-status]").first()).toBeVisible();
  // skills are approved in Setup, never here
  await expect(page.getByRole("button", { name: /approve/i })).toHaveCount(0);
  await page.getByRole("navigation", { name: "Subjects" }).getByRole("link", { name: "English" }).click();
  await expect(page.locator("tr[data-topic^='ENG']").first()).toBeVisible();
});

test("Today's line opens it, and Curriculum links to it instead of carrying the switches", async ({ page }) => {
  await page.goto("/today?kind=taught");
  const row = page.locator("tr[data-kind=taught]").first();
  if (await row.count()) {
    await row.getByRole("link").click();
    await expect(page).toHaveURL(/\/taught\?topic=/);
  }
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Not taught yet", exact: true })).toHaveCount(0);
  await page.locator("[data-ux=next]").click();
  await expect(page).toHaveURL(/\/taught$/);
});
