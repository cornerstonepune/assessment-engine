import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper, aWorksheet } from "./rows";

// Every screen must render its heading at a laptop and at a phone, with no console error and no
// sideways scroll. A teacher on a phone in a corridor is a real case.
const ROUTES: [string, string][] = [
  ["/today", "Today"],
  ["/", "Curriculum"],
  ["/library", "Question bank"],
  ["/worksheets", "Worksheets"],
  ["/papers", "Papers"],
  ["/papers/make", "Make papers"],
  ["/capture", "Marking"],
  ["/growth", "Children"],
  ["/home", "Home Assignments"],
];

const SIZES = [
  { name: "laptop", width: 1440, height: 900 },
  { name: "phone", width: 400, height: 860 },
];

// A child of the test's own (tests/rows.ts) with signed-off answers and a paper read: these two screens took the
// first class live listed, and skipped themselves on a database with none (goals/p1-browser-tests-in-ci.yaml).
const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
let kavya = "";
test.beforeAll(async () => {
  ({ Kavya: kavya } = await aClass(sql, "SCREENS-TEST", "G2", ["Kavya"]));
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${kavya}`;
  for (let i = n; i < 4; i++) {
    await sql`
      insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                  observed_at, confirmed_by)
      select tenant_id, id, 'NUM.OPS.01', 'R22', true, '{}', 'item', now(), 'e2e' from child where id = ${kavya}`;
  }
  await sql`select rebuild_child_skill_state(${kavya}::uuid)`;
  const w = await aWorksheet(sql, {
    code: "SCREENS-A", title: "Screens paper", date: "2026-09-01", band: "G2", week: "SCREENS-TEST",
    items: ["46 + 38", "57 + 28", "68 + 27"].map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
  });
  await aReadPaper(sql, {
    qr: "SCREENS-1", child: kavya, template: w.template, items: w.items,
    reads: [{ status: "correct", read: "84" }, { status: "wrong", read: "75" }, { status: "needs_teacher", read: "9 5" }],
  });
});
test.afterAll(async () => sql.end());

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
  for (const label of ["Today", "Children", "Papers", "Curriculum"]) {
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
  // the question bank is part of the Curriculum: its page marks Curriculum
  await page.goto("/library");
  await expect(page.getByRole("link", { name: "Curriculum" })).toHaveAttribute("aria-current", "page");
});

// A child's page reads in the school's own words: no rung, skill-set or mistake code reaches a teacher, and every skill
// with answers opens to the work behind it.
test("a child's page is in words, with the answers behind each skill", async ({ page }) => {
  await page.goto("/growth/class/SCREENS-TEST");
  await page.getByRole("table").getByRole("link").first().click();
  await expect(page).toHaveURL(/\/growth\/[0-9a-f-]{36}$/);
  const shown = page.getByRole("region", { name: "What their answers show" });
  await expect(shown).toBeVisible();
  await expect(shown).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z]+)\b/);
  // The page reads confirmed evidence and nothing else (rule 4): Kavya's four signed-off answers on 2-digit + 2-digit.
  const line = shown.locator("li[data-skill]").first();
  await expect(line).toBeVisible();
  await line.locator("summary").click();
  await expect(line.locator("details")).toHaveAttribute("open", "");
});

// The approval screen is reached by opening a paper, so it has no fixed path to list above. It is
// the one screen a teacher stands at with a photograph, and the one that must survive a phone.
for (const { name, width, height } of SIZES) {
  test(`${name} /capture/<paper>`, async ({ page }, testInfo) => {
    const errors: string[] = [];
    // The page images come from the engine, which is not running in CI. A missing image is a
    // broken <img>, not a broken screen, so those are the one thing not counted here.
    // A failed image names its address in the message's location, not its text.
    page.on(
      "console",
      (m) =>
        m.type() === "error" &&
        ![m.text(), m.location().url].some((t) => t.includes("/api/scan/")) &&
        errors.push(`${m.text()} ${m.location().url}`),
    );
    await page.setViewportSize({ width, height });
    await page.goto("/capture", { waitUntil: "networkidle" });
    // Capture & Mark lists students; a student lists their papers (Nimish, 2026-09-22).
    await page.locator(`a[href="/capture?child=${kavya}"]`).first().click();
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
