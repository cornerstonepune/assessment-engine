/**
 * U53 — The menu is the educator's week (goals/uxn3-the-menu.yaml). Nimish, 2026-10-22: "make sure that the navigation and
 * all the menu items are perfect", "complete, in the order of the educator's week". Each step of the week is a menu item
 * named as its page is titled; the current page is marked; only What needs doing carries a count; nothing in it names a subject.
 */
import { expect, test } from "@playwright/test";

const GROUPS = ["What needs doing", "Teaching", "Assessments", "Results", "Setup"];
// every page of the week, with the group it is in and the words of its own title (or its tab)
const PAGES = [
  ["/today", "What needs doing", "What needs doing"],
  ["/taught", "Teaching", "Teaching"],
  ["/papers/approve", "Assessments", "Papers to approve"],
  ["/papers", "Assessments", "Assessments"],
  ["/capture", "Assessments", "Upload papers"],
  ["/capture/check", "Assessments", "Check answers"],
  ["/growth", "Results", "Class results"],
  ["/", "Setup", "Curriculum"],
  ["/library", "Setup", "Question bank"],
] as const;

test("the menu lists the five groups in order, and each page is marked and titled by its own words", async ({ page }) => {
  await page.goto("/today");
  const menu = page.getByRole("navigation", { name: "Sections" });
  const names = (await menu.getByRole("link").allInnerTexts()).map((n) => n.replace(/\s*\d[\d,]*$/, "").trim());
  expect(names).toEqual(GROUPS);
  for (const [path, group, label] of PAGES) {
    await page.goto(path);
    await expect(menu.locator("[aria-current=page]"), path).toHaveText(new RegExp(`^${group}`));
    // the page says the same words in its title, above it, or in its stage line
    await expect(page.getByTestId("stage"), path).toContainText(label);
  }
});

test("only What needs doing carries a count, and no word of the menu names a subject", async ({ page }) => {
  await page.goto("/growth");
  const menu = page.getByRole("navigation", { name: "Sections" });
  await expect(menu.getByTestId("waiting")).toHaveCount(1);
  await expect(menu.getByRole("link", { name: /^What needs doing/ }).getByTestId("waiting")).toBeVisible();
  expect(await menu.innerText()).not.toMatch(/\b(maths|english|hindi|science|evs)\b/i);
  await page.getByRole("button", { name: "Menu" }).click();
  expect(await page.getByRole("dialog", { name: "Menu" }).innerText()).not.toMatch(/\b(maths|english|hindi|science|evs)\b/i);
});

test("no step of the week is a dead end: each page of the menu ends on a next step or opens one", async ({ page }) => {
  for (const [path] of PAGES) {
    await page.goto(path);
    // a page on the shared blocks has its next-step link; Marking and the old Today open the places to do each thing
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const next = await page.locator("[data-ux=next]").count();
    expect(next + (await page.getByRole("main").getByRole("link").count()), `${path}: a way on`).toBeGreaterThan(0);
  }
  await page.goto("/taught");
  await expect(page.locator("[data-ux=next]")).toHaveAttribute("href", "/papers");
});
