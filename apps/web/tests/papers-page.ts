import { expect, type Page } from "@playwright/test";

/** Assessments' one button (goals/s2b-assessments-declutter.yaml): open it, and the four ways are links. */
export async function openMake(page: Page) {
  await page.getByText("Make an assessment", { exact: true }).click();
}

/** Assessments' one Filter: open it, choose by field name (stage, topic, class, child, kind, week), and show. */
export async function filterBy(page: Page, chosen: Record<string, { label: string } | { value: string }>) {
  await page.getByText("Filter", { exact: true }).click();
  const form = page.locator("[data-filters] form");
  for (const [name, how] of Object.entries(chosen)) await form.locator(`select[name=${name}]`).selectOption(how);
  await form.getByRole("button", { name: "Show" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Assessments");
}
