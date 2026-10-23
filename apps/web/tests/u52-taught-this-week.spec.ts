/**
 * U52 — Taught this week is a page of its own (goals/uxn2-taught-this-week.yaml). Nimish, 2026-10-22: "make it easy to
 * navigate", the menu "in the order of the educator's week". Wednesday's step, saying what was taught, was the top of
 * the Curriculum page. It is now its own page, with the one main action and the week's next step; Today's line opens it,
 * and Curriculum links to it instead of carrying it.
 */
import { expect, test } from "@playwright/test";

test("Taught this week is its own page: its main action, the topics not taught yet, and the week's next step", async ({ page }) => {
  await page.goto("/taught");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Taught this week");
  await expect(page.locator("[data-ux=action]").getByRole("link", { name: "Say what was taught" })).toHaveAttribute("href", "#not-taught");
  await expect(page.locator("[data-ux=next]")).toHaveAttribute("href", "/papers/approve");
  await expect(page.getByRole("region", { name: "Not taught yet", exact: true })).toBeVisible();
});

test("Today's line opens it, and Curriculum links to it instead of carrying the switches", async ({ page }) => {
  await page.goto("/today");
  await page.getByRole("region", { name: "Topics not taught yet", exact: true }).getByRole("link").first().click();
  await expect(page).toHaveURL(/\/taught#not-taught$/);
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Not taught yet", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: /^Taught this week/ }).click();
  await expect(page).toHaveURL(/\/taught$/);
});
