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

// A child's page reads as a ladder in the school's own words: no rung, skill-set or mistake code
// reaches a teacher, and every rung with answers opens to the work behind it.
test("a child's ladder is in words, with the answers behind each rung", async ({ page }) => {
  await page.goto("/growth");
  await page.getByRole("main").getByRole("link").first().click();
  await expect(page).toHaveURL(/\/growth\/[0-9a-f-]{36}$/);
  const ladder = page.getByRole("list", { name: "The ladder" });
  await expect(ladder.getByRole("listitem").first()).toBeVisible();
  await expect(ladder).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z]+)\b/);
  await expect(ladder.getByRole("table")).toHaveCount(0);
  await ladder.getByRole("link").first().click();
  const opened = ladder.locator(":target");
  await expect(opened.getByRole("table")).toBeVisible();
  await expect(opened.getByRole("columnheader", { name: "Child wrote" })).toBeVisible();
});

// The approval screen is reached by opening a paper, so it has no fixed path to list above. It is
// the one screen a teacher stands at with a photograph, and the one that must survive a phone.
for (const { name, width, height } of SIZES) {
  test(`${name} /capture/<paper>`, async ({ page }, testInfo) => {
    const errors: string[] = [];
    // The page images come from the engine, which is not running in CI. A missing image is a
    // broken <img>, not a broken screen, so those are the one thing not counted here.
    page.on("console", (m) => m.type() === "error" && !m.text().includes("/api/scan/") && errors.push(m.text()));
    await page.setViewportSize({ width, height });
    await page.goto("/capture", { waitUntil: "networkidle" });
    const open = page.getByRole("table").first().getByRole("link").first();
    if ((await open.count()) === 0) test.skip(true, "no paper has been read yet");
    await open.click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("·");
    await expect(page.getByRole("heading", { name: "What this paper says, by skill" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, "page must not scroll sideways").toBeLessThanOrEqual(1);
    expect(errors).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`${name}-capture-paper.png`), fullPage: true });
  });
}
