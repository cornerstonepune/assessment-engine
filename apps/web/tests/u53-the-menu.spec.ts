/**
 * U53 — The menu is the educator's week (goals/uxn3-the-menu.yaml). Nimish, 2026-10-22: "make sure that the navigation and
 * all the menu items are perfect", "complete, in the order of the educator's week". Each step of the week is a menu item
 * named as its page is titled; the current page is marked; only Today carries a count; nothing in it names a subject.
 */
import { expect, test } from "@playwright/test";

const WEEK = [
  ["/today", "Today"],
  ["/taught", "Taught this week"],
  ["/papers/approve", "Papers to approve"],
  ["/papers", "Assessments"],
  ["/capture", "Upload papers"],
  ["/capture/check", "Check answers"],
  ["/growth", "Class results"],
] as const;
const SETUP = [
  ["/", "Curriculum"],
  ["/library", "Question bank"],
] as const;

test("the menu lists the week's steps in order, then the setup apart, and each page is marked and titled by its own words", async ({ page }) => {
  await page.goto("/today");
  const menu = page.getByRole("navigation", { name: "Sections" });
  const names = (await menu.getByRole("link").allInnerTexts()).map((n) => n.replace(/\s*\d[\d,]*$/, "").trim());
  expect(names).toEqual([...WEEK, ...SETUP].map(([, label]) => label));
  await expect(menu.locator("[data-nav-group]")).toHaveText(["This week", "Setup"]);
  for (const [path, label] of [...WEEK, ...SETUP]) {
    await page.goto(path);
    await expect(menu.locator("[aria-current=page]"), path).toHaveText(new RegExp(`^${label}`));
    // the page says the same words in its title, above it, or in its stage line
    await expect(page.getByTestId("stage"), path).toContainText(label);
  }
});

test("only Today carries a count, and no word of the menu names a subject", async ({ page }) => {
  await page.goto("/growth");
  const menu = page.getByRole("navigation", { name: "Sections" });
  await expect(menu.getByTestId("waiting")).toHaveCount(1);
  await expect(menu.getByRole("link", { name: /^Today/ }).getByTestId("waiting")).toBeVisible();
  expect(await menu.innerText()).not.toMatch(/\b(maths|english|hindi|science|evs)\b/i);
});

test("no step of the week is a dead end: each page of the menu ends on a next step or opens one", async ({ page }) => {
  for (const [path] of WEEK) {
    await page.goto(path);
    // a page on the shared blocks has its next-step link; Marking and Today open the places to do each thing
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const next = await page.locator("[data-ux=next]").count();
    expect(next + (await page.getByRole("main").getByRole("link").count()), `${path}: a way on`).toBeGreaterThan(0);
  }
  await page.goto("/taught");
  await expect(page.locator("[data-ux=next]")).toHaveAttribute("href", "/papers/approve");
});
