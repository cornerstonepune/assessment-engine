// Managed by the Athena harness: reinstalling overwrites this file.
// Every journey test imports `test` and `expect` from here instead of @playwright/test. After each test it
// checks the page with axe (accessibility) and compares screenshots at phone, tablet and desktop widths.
// A screenshot baseline changes only in a pull request whose description shows the before and after images
// (`athena baseline-check`). Needs @playwright/test and @axe-core/playwright in this app's devDependencies.
import { test as base, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

export const viewports = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 820, height: 1180 },
  { name: "desktop", width: 1440, height: 900 },
];

export const test = base.extend<{ journeyChecks: void }>({
  journeyChecks: [
    async ({ page }, use, testInfo) => {
      await use();
      if (testInfo.status !== testInfo.expectedStatus || page.url() === "about:blank") return;
      const axe = await new AxeBuilder({ page }).analyze();
      expect(axe.violations, "accessibility (axe) violations").toEqual([]);
      const slug = testInfo.titlePath.slice(1).join("-").toLowerCase().replace(/[^a-z0-9]+/g, "-");
      for (const v of viewports) {
        await page.setViewportSize({ width: v.width, height: v.height });
        await expect(page).toHaveScreenshot(`${slug}-${v.name}.png`, { fullPage: true });
      }
    },
    { auto: true },
  ],
});

export { expect };
