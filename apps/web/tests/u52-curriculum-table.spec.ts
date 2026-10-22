/**
 * U52 — Curriculum is a table (goals/uxn2-curriculum-table.yaml). Nimish, 2026-10-22: "the tags of subject names and all
 * are never aligned, like on the curriculum page ... Can we use tables more for easier viewing, and use icons or red, amber,
 * green ... Use filters wherever possible." Read as it renders at 1440 px: a skill to a row, grade, subject, topic, skill,
 * levels and status as columns, one chip for the state, one filter row, ten rows to a page.
 */
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1440, height: 900 } });

test("Curriculum is one table of skills: grade, subject, topic, skill, levels, status", async ({
  page,
}) => {
  await page.goto("/");
  const table = page.getByRole("table", { name: "The curriculum" });
  await expect(table).toBeVisible();
  const heads = await table.locator("thead th").allTextContents();
  expect(heads.map((h) => h.trim())).toEqual([
    "Grade",
    "Subject",
    "Topic",
    "Skill",
    "Levels",
    "Status",
  ]);
  expect(await table.locator("tbody tr").count()).toBeLessThanOrEqual(10);
  // nothing to open: no tree, no "Open everything"
  await expect(
    page.getByRole("button", { name: "Open everything" }),
  ).toHaveCount(0);
  // every row's grade sits in its own column, and each status is an icon and a word (never colour alone)
  const first = table.locator("tbody tr").first();
  await expect(first.locator("td").nth(0)).toContainText(/^Grade \d/);
  const chip = first.locator("[data-status]");
  await expect(chip.locator("svg")).toHaveCount(1);
  await expect(chip).not.toHaveText("");
});

test("the filter row narrows the table and one click clears it", async ({
  page,
}) => {
  await page.goto("/");
  const bar = page.locator("[data-filterbar]");
  await expect(bar).toBeVisible();
  const all = await page
    .getByRole("table", { name: "The curriculum" })
    .locator("tbody tr")
    .count();
  await page.goto("/?grade=G1");
  const rows = page
    .getByRole("table", { name: "The curriculum" })
    .locator("tbody tr");
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(0);
  for (const g of await rows.locator("td:first-child").allInnerTexts())
    expect(g.trim()).toBe("Grade 1");
  await expect(page.locator("[data-active-filters]")).toContainText(
    "Grade: Grade 1",
  );
  await page.getByRole("link", { name: "Clear" }).click();
  await expect(page).toHaveURL(/\/$/);
  expect(
    await page
      .getByRole("table", { name: "The curriculum" })
      .locator("tbody tr")
      .count(),
  ).toBe(all);
});

test("a search finds a skill, and the skill's link opens its page", async ({
  page,
}) => {
  await page.goto("/?q=adds");
  const rows = page
    .getByRole("table", { name: "The curriculum" })
    .locator("tbody tr");
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(0);
  await rows.first().locator("a").first().click();
  await expect(page).toHaveURL(/\/skill-sets\//);
});
