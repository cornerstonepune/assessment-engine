/**
 * The sign-in gate, against a server with the development bypass off — the way it runs at school.
 * A gate that is only tested with the bypass on is not tested at all.
 */
import { expect, test } from "@playwright/test";

const ROUTES = ["/", "/worksheets", "/library", "/capture", "/growth", "/home", "/skill-sets/SUB.2D2D"];

for (const route of ROUTES) {
  test(`no session: ${route} sends you to sign in`, async ({ page }) => {
    await page.goto(route);
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in");
  });
}

test("a wrong password is refused and you stay on the sign-in page", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("School email").fill("nimish.shah1989@gmail.com");
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Scoped to main, because Next's own route announcer is also role="alert".
  await expect(page.getByRole("main").getByRole("alert")).toContainText("do not match");
  await expect(page).toHaveURL(/\/login/);
});
