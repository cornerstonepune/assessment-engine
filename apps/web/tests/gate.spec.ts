/**
 * The sign-in gate, against a server with the development bypass off — the way it runs at school.
 * A gate that is only tested with the bypass on is not tested at all.
 */
import { expect, test } from "@playwright/test";

const ROUTES = ["/", "/worksheets", "/library", "/capture", "/growth", "/home", "/skill-sets/SUB.2D.EXCH"];

for (const route of ROUTES) {
  test(`no session: ${route} sends you to sign in`, async ({ page }) => {
    await page.goto(route);
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in");
  });
}

test("the sign-in page says plainly when it is not configured, rather than failing silently", async ({ page }) => {
  await page.goto("/login");
  const email = page.getByLabel("School email");
  await expect(email).toBeVisible();
  // Either it is configured and the field works, or it says why it cannot. Scoped to main, because
  // Next's own route announcer is also role="alert" and would make the match ambiguous.
  if (await email.isDisabled()) {
    await expect(page.getByRole("main").getByRole("alert")).toContainText("not configured");
  } else {
    await expect(page.getByRole("button", { name: "Send me a link" })).toBeEnabled();
  }
});
