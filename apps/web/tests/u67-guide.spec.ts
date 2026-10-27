/**
 * U67 — the Guide (goals/guide_for_educators.yaml). Nimish, 27 Oct 2026: "Can we create a guide page where everything is
 * well explained through right visuals and menu navigation etc., so that people don't come to me: the core capabilities
 * around each module, what to see where, how something is defined or calculated, the workflows inside, all explained in
 * ELI5 terms for educators so that it's a transparent system."
 *
 * The guide's words are held to the menu, the map, the routes, the buttons and the threshold rows with no database by
 * packages/engine/tests/test_guide.py; this is the guide as an educator meets it, at desktop and phone width.
 */
import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import postgres from "postgres";
import { GROUPS } from "../lib/menu";
import { slugOf } from "../lib/guide-path";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(() => sql.end());

const MAP = JSON.parse(readFileSync(path.resolve(__dirname, "../../../workflows.json"), "utf8")) as {
  workflows: { code: string; name: string; steps: string[] }[];
  steps: { code: string }[];
};
const MENU = GROUPS.flatMap((g) => g.pages);
const GUIDE = ["/guide", ...MENU.map((p) => `/guide/${slugOf(p.label)}`), "/guide/workflows", "/guide/worked-out", "/guide/words", "/guide/report-a-problem"];

test("start here draws the whole flow from the map and the menu from the real menu", async ({ page }) => {
  await page.goto("/guide");
  await expect(page.getByRole("heading", { level: 1, name: "Start here" })).toBeVisible();
  const flow = page.locator("[data-drawing=flow]");
  for (const w of MAP.workflows) {
    await expect(flow.locator(`[data-stage=${w.code}]`)).toContainText(w.name);
    for (const code of w.steps) await expect(flow.locator(`[data-step=${code}]`)).toBeVisible();
  }
  await expect(flow.locator("[data-step]")).toHaveCount(MAP.steps.length);
  const menu = page.locator("[data-drawing=menu]");
  for (const g of GROUPS) await expect(menu.getByRole("region", { name: g.label })).toBeVisible();
  for (const p of MENU) await expect(menu.getByRole("link", { name: p.label, exact: true }).first()).toHaveAttribute("href", `/guide/${slugOf(p.label)}`);
});

test("each I want to button lands on its answer", async ({ page }) => {
  await page.goto("/guide");
  const wants = page.locator("[data-wants] a");
  const hrefs = await wants.evaluateAll((as) => as.map((a) => a.getAttribute("href")!));
  expect(hrefs.length).toBeGreaterThanOrEqual(8);
  for (const href of hrefs) {
    await page.goto(href);
    const id = href.split("#")[1];
    await expect(page.locator(`[id="${id}"]`), `${href} lands on no section`).toBeVisible();
    await expect(page.locator(`[id="${id}"] h2`)).not.toBeEmpty();
  }
});

test("every menu item's guide page opens, in the menu's order, with its labelled drawing", async ({ page }) => {
  await page.goto("/guide");
  const nav = page.getByRole("navigation", { name: "The guide" }).getByRole("link");
  await expect(nav).toHaveCount(GUIDE.length);
  const order = await nav.allInnerTexts();
  expect(order.slice(1, 1 + MENU.length)).toEqual(MENU.map((p) => p.label));
  for (const p of MENU) {
    await page.goto(`/guide/${slugOf(p.label)}`);
    await expect(page.getByRole("heading", { level: 1, name: p.label, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: `Open ${p.label}` })).toHaveAttribute("href", p.href);
    const drawing = page.locator("[data-drawing=page]");
    await expect(drawing).toBeVisible();
    const boxes = await drawing.locator("[aria-hidden=true] li").count();
    expect(boxes, `${p.label}: the drawing has too few parts`).toBeGreaterThanOrEqual(3);
    // the drawing is said again in words, one line for each box
    await expect(drawing.locator(":scope > ol > li")).toHaveCount(boxes);
    for (const id of ["for", "layout", "buttons"]) await expect(page.locator(`[id="${id}"]`)).toBeVisible();
  }
});

test("a number in the guide is the row in force: change the row and the guide changes", async ({ page }) => {
  const [row] = await sql<{ value: number }[]>`select value::float as value from threshold where key = 'calibration.too_easy_share'`;
  const pc = (v: number) => `${Math.round(v * 100)}%`;
  const section = page.locator("#levels-to-review");
  try {
    await page.goto("/guide/worked-out");
    await expect(section).toContainText(`When ${pc(row.value)} or more`);
    await sql`update threshold set value = 0.75 where key = 'calibration.too_easy_share'`;
    await page.reload();
    await expect(section).toContainText("When 75% or more");
  } finally {
    await sql`update threshold set value = ${row.value} where key = 'calibration.too_easy_share'`;
  }
  await page.reload();
  await expect(section).toContainText(`When ${pc(row.value)} or more`);
  const [min] = await sql<{ value: number }[]>`select value::int as value from threshold where key = 'calibration.min_children'`;
  await expect(section).toContainText(`fewer than ${min.value} children assessed`);
});

test("the workflows page shows every step of the map in its four stages, with who does it", async ({ page }) => {
  await page.goto("/guide/workflows");
  for (const w of MAP.workflows) {
    const stage = page.locator(`[id="stage-${w.code}"]`);
    await expect(stage.getByRole("heading", { level: 2 })).toHaveText(w.name);
    for (const code of w.steps) {
      const step = stage.locator(`li[id="${code}"]`);
      await expect(step).toBeVisible();
      await expect(step.locator("[data-who]")).toContainText(/Who: (educator|coordinator|the engine)/);
    }
  }
  await expect(page.locator("li[data-step][id]")).toHaveCount(MAP.steps.length);
});

test("the glossary and why did it say that", async ({ page }) => {
  await page.goto("/guide/words");
  for (const q of ["Why was an answer left for a person to check?", "Why does a child's grade differ from the class's?", "Why did a wrong answer count against another skill?"]) {
    await expect(page.getByRole("heading", { level: 2, name: q })).toBeVisible();
  }
  // the states and the levels are the rows' own words
  const [grey] = await sql<{ count_words: string }[]>`select count_words from state_colour where code = 'grey'`;
  await expect(page.locator("#why-too-few h2")).toContainText(grey.count_words);
  const levels = await sql<{ code: string }[]>`select code from difficulty order by ord`;
  for (const l of levels) await expect(page.locator("#level")).toContainText(l.code);
  await page.goto("/guide/worked-out");
  const states = await sql<{ words: string }[]>`select words from child_state order by ord`;
  for (const s of states) await expect(page.locator("[data-drawing=states]")).toContainText(s.words);
});

test("the help mark on a page's header opens that page's guide, and the menu has the Guide", async ({ page }) => {
  for (const [href, label] of [["/papers", "Assessments"], ["/capture/check", "Check answers"], ["/staff", "Staff"]]) {
    await page.goto(href);
    await page.locator("[data-ux=help]").click();
    await expect(page).toHaveURL(new RegExp(`/guide/${slugOf(label)}$`));
    await expect(page.getByRole("heading", { level: 1, name: label, exact: true })).toBeVisible();
  }
  // the guide's own pages carry no "?" of their own
  await expect(page.locator("[data-ux=help]")).toHaveCount(0);
  await page.goto("/today");
  await page.getByRole("button", { name: "Menu" }).click();
  await page.locator("#site-menu").getByRole("link", { name: "Guide", exact: true }).click();
  await expect(page).toHaveURL(/\/guide$/);
});

test("every guide page reads at phone width with no sideways scroll", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const href of GUIDE) {
    await page.goto(href);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const wide = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(wide, `${href} scrolls sideways by ${wide}px on a phone`).toBeLessThanOrEqual(1);
  }
});
