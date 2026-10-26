/**
 * U52 — Saying what was taught is a row of What needs doing (goals/nav3_what_needs_doing.yaml). Nimish, 2026-10-22: "make it
 * easy to navigate"; 26 Oct 2026: "I don't understand the purpose of this teaching page". Wednesday's step is one group of
 * What needs doing, a row for each topic with its own button; Curriculum's next step is What needs doing, and its old page's
 * address opens it.
 */
import { expect, test } from "@playwright/test";

test("a topic waiting to be marked taught is a row with its own button, in the group that opens Curriculum", async ({ page }) => {
  await page.goto("/today?kind=taught");
  const group = page.locator("details[data-group=taught]");
  await expect(group.locator("a[data-group-home]")).toHaveAttribute("href", "/");
  const rows = group.locator("tr[data-kind=taught]");
  expect(await rows.count()).toBeGreaterThan(0);
  for (const row of await rows.all()) await expect(row.getByRole("button", { name: "Mark as taught" })).toHaveCount(1);
  // skills are approved in Setup, never here
  await expect(group.getByRole("button", { name: /approve/i })).toHaveCount(0);
});

test("Curriculum's next step is What needs doing", async ({ page }) => {
  await page.goto("/");
  await page.locator("[data-ux=next]").click();
  await expect(page).toHaveURL(/\/today$/);
});
