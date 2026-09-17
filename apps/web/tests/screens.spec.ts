import { expect, test } from "@playwright/test";

// Every screen must render its heading at a laptop and at a phone, with no console error and no
// sideways scroll. A teacher on a phone in a corridor is a real case.
const ROUTES: [string, string][] = [
  ["/", "Skill Map"],
  ["/skill-sets/SUB.2D.EXCH", "2-digit subtraction with exchange"],
  ["/library", "Question bank"],
  ["/worksheets", "Worksheets"],
  ["/capture", "Capture & Mark"],
  ["/growth", "Child Growth"],
  ["/home", "Home Assignments"],
];

const SIZES = [
  { name: "laptop", width: 1440, height: 900 },
  { name: "phone", width: 400, height: 860 },
];

for (const { name, width, height } of SIZES) {
  for (const [path, heading] of ROUTES) {
    test(`${name} ${path}`, async ({ page }, testInfo) => {
      const errors: string[] = [];
      page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
      await page.setViewportSize({ width, height });
      await page.goto(path, { waitUntil: "networkidle" });

      await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, "page must not scroll sideways").toBeLessThanOrEqual(1);
      expect(errors).toEqual([]);

      await page.screenshot({ path: testInfo.outputPath(`${name}${path.replace(/\W+/g, "-")}.png`), fullPage: true });
    });
  }
}

test("every section is reachable from the menu", async ({ page }) => {
  await page.goto("/");
  for (const label of ["Worksheets", "Question bank", "Capture & Mark", "Child Growth", "Home Assignments"]) {
    await expect(page.getByRole("navigation").getByRole("link", { name: label })).toBeVisible();
  }
});

test("the menu marks where you are", async ({ page }) => {
  await page.goto("/library");
  await expect(page.getByRole("link", { name: "Question bank" })).toHaveAttribute("aria-current", "page");
});
