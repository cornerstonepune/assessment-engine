/**
 * M1-09 — the parts every page shares are big enough for a thumb (D-073, R2; docs/design-audit-k2.md): the header's "?",
 * the next step at the foot of a page, and the site's .btn and .chip, at least 44 px each way, on a desktop and a phone.
 * The page is Assessments, a menu page with both; no rows of its own.
 */
import { expect, test, type Page } from "@playwright/test";

test("the header's ? and the page's next step are at least 44 px each way at 1280 px", ({
  page,
}) => taps(page, 1280));
test("the header's ? and the page's next step are at least 44 px each way at 390 px", ({
  page,
}) => taps(page, 390));

async function taps(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto("/papers");
  for (const sel of ["[data-ux=help]", "[data-ux=next]"]) {
    await expect(page.locator(sel).first()).toBeVisible();
    const box = await page.locator(sel).first().boundingBox();
    expect(box, sel).not.toBeNull();
    expect(Math.round(box!.height), `${sel} height`).toBeGreaterThanOrEqual(44);
    expect(Math.round(box!.width), `${sel} width`).toBeGreaterThanOrEqual(44);
  }
  for (const sel of [".btn", ".chip"]) {
    const heights = await page
      .locator(`main ${sel}:visible`)
      .evaluateAll((els) =>
        els.map((e) => Math.round(e.getBoundingClientRect().height)),
      );
    for (const h of heights)
      expect(h, `${sel} height`).toBeGreaterThanOrEqual(44);
  }
}
