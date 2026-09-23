import { expect, test } from "@playwright/test";

// Every screen must render its heading at a laptop and at a phone, with no console error and no
// sideways scroll. A teacher on a phone in a corridor is a real case.
const ROUTES: [string, string][] = [
  ["/today", "Today"],
  ["/", "Skill Map"],
  ["/library", "Question bank"],
  ["/worksheets", "Worksheets"],
  ["/capture", "Capture & Mark"],
  ["/growth", "Children"],
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
  for (const label of ["Today", "Children", "Marking", "Papers", "Curriculum", "Question bank"]) {
    await expect(page.getByRole("navigation").getByRole("link", { name: label, exact: true })).toBeVisible();
  }
});

// Unlayered, the global `a:hover` beat the sidebar's own hover colour and drew a menu item basalt on
// basalt: it vanished under the pointer.
test("a menu item stays readable while the pointer is on it", async ({ page }) => {
  await page.goto("/");
  const sidebar = await page.locator("aside").evaluate((el) => getComputedStyle(el).backgroundColor);
  for (const item of await page.getByRole("navigation").getByRole("link").all()) {
    await item.hover();
    const colour = await item.evaluate((el) => getComputedStyle(el).color);
    expect(colour, (await item.textContent()) ?? "").not.toBe(sidebar);
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
  await expect(page).toHaveURL(/\/growth\/class\//);
  await page.getByRole("table").getByRole("link").first().click();
  await expect(page).toHaveURL(/\/growth\/[0-9a-f-]{36}$/);
  const ladder = page.getByRole("list", { name: "The ladder" });
  await expect(ladder.getByRole("listitem").first()).toBeVisible();
  await expect(ladder).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z]+)\b/);
  await expect(ladder.getByRole("table")).toHaveCount(0);
  // A rung only opens once someone has signed off answers on it — the graph reads confirmed
  // evidence and nothing else (rule 4). Straight after the corpus was re-read there is a ladder to
  // look at and nothing behind any rung of it, and that is the system working, not failing.
  const rung = ladder.getByRole("link").first();
  if ((await rung.count()) === 0) test.skip(true, "no paper has been signed off yet");
  await rung.click();
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
    // Capture & Mark lists students; a student lists their papers (Nimish, 2026-09-22).
    const student = page.getByRole("table").filter({ has: page.getByRole("link") }).first().getByRole("link").first();
    if ((await student.count()) === 0) test.skip(true, "no paper has been read yet");
    await student.click();
    await expect(page).toHaveURL(/child=/); // the student's own papers, not the list still on screen
    await page.getByRole("table").first().getByRole("link").first().click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("·");
    await expect(page.getByRole("heading", { name: "What this paper says, by skill" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, "page must not scroll sideways").toBeLessThanOrEqual(1);
    expect(errors).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`${name}-capture-paper.png`), fullPage: true });
  });
}
