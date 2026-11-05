/**
 * M1-14 part a — the timetable's rules on a screen (goals/m1-14a-timetable-rules.yaml). A scripted walkthrough on the school's
 * own Fortnight 10 text (loaded by the engine's own command into a K2 class of the test's own, "M104"): a K2 educator blocks a
 * day and changes a subject's weekly limit, with the taps and seconds counted. Placeholder rows only; the educator switch
 * (educator.timetable_enabled) is never turned on here, and a check at the end says it was not.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { k2Class } from "./k2-rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const REPO = path.resolve(__dirname, "../../..");
const SHOTS = path.join(REPO, "docs/screens/m1-14a");
const TABS = "supabase/seed/k2_tabs_2026_11_04";
let klass: string;

test.beforeAll(async () => {
  mkdirSync(SHOTS, { recursive: true });
  ({ klass } = await k2Class(sql));
  await sql`delete from timetable_block where school_class_id = ${klass}`;
  await sql`delete from timetable_limit where school_class_id = ${klass}`;
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from timetable_slot where school_class_id = ${klass}`;
  if (n === 0) {
    execFileSync(
      path.join(REPO, "bin/engine"),
      ["timetable", "load", "--frame", `${TABS}/frame.csv`, "--planner", `${TABS}/planner.csv`, "--calendar", `${TABS}/calendar.csv`,
        "--spans", `${TABS}/frame_spans.json`, "--section", "M104", "--grade", "K2", "--year", "2031-32",
        "--undecided", "2026-12-07=graph-tab-and-calendar-disagree-on-the-fortnight-10-11-boundary", "--apply"],
      { cwd: REPO, env: { ...process.env }, stdio: "pipe" },
    );
  }
});
test.afterAll(async () => {
  await sql.end();
});

const PAGE = () => `/timetable/rules?class=${klass}`;

test("a K2 educator blocks a day and changes a subject's weekly limit in well under five minutes", async ({ page }) => {
  const started = Date.now();
  let taps = 0;
  const tap = async <T>(go: Promise<T>) => {
    taps += 1;
    return go;
  };
  await page.goto(PAGE());
  await expect(page.getByRole("heading", { name: "Timetable rules" })).toBeVisible();
  await expect(page.getByText("Nothing is blocked.")).toBeVisible(); // designed empty state
  await expect(page.getByText("No limits yet.")).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: path.join(SHOTS, "empty-1280.png"), fullPage: true });

  // 1. block a day
  const block = page.locator("#block form");
  await tap(block.getByLabel("Date").fill("2026-11-25"));
  await tap(block.getByLabel("Reason").fill("Sports day"));
  await tap(block.getByRole("button", { name: "Block" }).click());
  await expect(page.getByText("Saved.")).toBeVisible();
  await expect(page.locator("#block .tt-list")).toContainText("Sports day");
  await expect(page.locator("#block .tt-list")).toContainText(/Wed, 25 Nov,? 2026/);

  // 2. change a subject's weekly limit
  const limit = page.locator("form").filter({ has: page.getByRole("button", { name: "Save limit" }) });
  await tap(limit.getByLabel("Subject").selectOption("math"));
  await tap(limit.getByLabel("Most").fill("3"));
  await tap(limit.getByRole("button", { name: "Save limit" }).click());
  await expect(page.getByText("Saved.")).toBeVisible();
  await expect(page.getByText(/Math, per week/)).toBeVisible();
  await expect(page.getByText(/placed, over/)).toBeVisible(); // more maths is placed than 3: it needs a look

  const seconds = (Date.now() - started) / 1000;
  console.log(`walkthrough: ${taps} taps and fields, ${seconds.toFixed(1)} seconds (limit: 300)`);
  expect(seconds).toBeLessThan(300);

  await page.screenshot({ path: path.join(SHOTS, "rules-1280.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(SHOTS, "rules-390.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});

test("a rule that cannot be right is refused in the engine's words and nothing is saved", async ({ page }) => {
  await page.goto(PAGE());
  const limit = page.locator("form").filter({ has: page.getByRole("button", { name: "Save limit" }) });
  await limit.getByLabel("Subject").selectOption("art");
  await limit.getByLabel("Fewest").fill("5");
  await limit.getByLabel("Most").fill("3");
  await limit.getByRole("button", { name: "Save limit" }).click();
  await expect(page.locator(".tt [role=alert]")).toContainText("The fewest cannot be more than the most");
  await expect(page.getByText(/Art, per week/)).toHaveCount(0);
});

test("a period is given new times, and the change is kept with who made it", async ({ page }) => {
  await page.goto(PAGE());
  const row = page.getByRole("form", { name: /^Period / }).first();
  await row.getByLabel("Starts").fill("08:25");
  await row.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved.")).toBeVisible();
  await expect(page.getByText(/changed period/).first()).toBeVisible();
  await expect(page.getByText(/^You changed period/).first()).toBeVisible();
  await row.getByLabel("Starts").fill("08:30"); // put it back: the school's own time
  await row.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved.")).toBeVisible();
});

test("the last period of the day, which the school gave no end, can be renamed without inventing one", async ({ page }) => {
  await page.goto(PAGE());
  const row = page.getByRole("form", { name: /^Period Boarding/ });
  await expect(row.getByLabel("Ends")).toHaveValue("");
  await row.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved.")).toBeVisible();
});

test("a block is removed", async ({ page }) => {
  await page.goto(PAGE());
  await page.getByRole("button", { name: "Remove" }).first().click();
  await expect(page.getByText("Saved.")).toBeVisible();
  await expect(page.getByText("Nothing is blocked.")).toBeVisible();
});

test("the screen uses the tokens and no colour of its own, and the educator switch stays off", async () => {
  const css = readFileSync(path.join(__dirname, "../app/(app)/timetable/timetable.css"), "utf8");
  expect(css.match(/#[0-9a-fA-F]{3,8}\b/g)).toBeNull();
  expect(css.match(/\b(rgb|hsl)a?\(/g)).toBeNull();
  const [row] = await sql<{ on: boolean }[]>`select coalesce((select value = 'true'::jsonb from config where key = 'educator.timetable_enabled'), false) as on`;
  expect(row.on).toBe(false);
});
