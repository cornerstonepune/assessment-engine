/**
 * M1-09 — the K2 educator's Today and This week as calendars (goals/m1-09c-educator-calendar.yaml, D-075, D-076), on
 * M1-06's /timetable routes with Fortnight 10 as the school wrote it, loaded by M1-06's own loader into the tests'
 * placeholder K2 class (packages/engine/tests/k2_timetable_rows.py). Every period a block with its time as time and the
 * school's words, coloured by its state; every block opens its period. No child anywhere.
 */
import path from "node:path";
import { execFileSync } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { displayFaceOnlyLarge, shoot, tapsAreBig, timetableSwitch } from "./educator-screens";
import { SECTION, k2Class } from "./k2-rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MONDAY = "2026-11-23"; // Fortnight 10, week A; Tuesday 24 is a holiday
let klass = "";

test.beforeAll(async () => {
  ({ klass } = await k2Class(sql));
  execFileSync("uv", ["run", "python", "tests/k2_timetable_rows.py", SECTION], { cwd: path.resolve(__dirname, "../../../packages/engine"), env: process.env, stdio: "pipe" });
});
test.afterAll(async () => {
  await timetableSwitch(sql, false);
  await sql.end();
});

const white = (page: Page) => page.locator("[data-educator]").evaluate((e) => getComputedStyle(e).backgroundColor);

test("while the timetable is switched off Today, This week and a period are not found", async ({ page }) => {
  await timetableSwitch(sql, false);
  for (const href of ["/educator", "/educator/week", "/educator/period/00000000-0000-0000-0000-000000000000"]) {
    await page.goto(href);
    await expect(page.getByText("This page could not be found.")).toBeVisible();
  }
});

test("Today is the day as a calendar: every period a block in time order, its time as time, the school's words, a chip only on work", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator?class=${klass}&day=${MONDAY}`);
  expect(await white(page)).toBe("rgb(255, 255, 255)");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Monday 23 November");
  await expect(page.getByRole("navigation", { name: "Where you are" })).toContainText("Monday 23 November");
  const blocks = page.locator(`[data-day="${MONDAY}"] [data-period]`);
  await expect(blocks).toHaveCount(15);
  const times = await blocks.locator("span.tabular-nums").allTextContents();
  expect(times[0]).toBe("08:30–08:45");
  expect([...times].sort()).toEqual(times);
  await expect(page.locator('[data-kind="fixed"]').first()).toContainText("Settling + Outdoor free play");
  await expect(page.locator('[data-kind="fixed"] [data-chip]')).toHaveCount(0);
  await expect(page.locator('[data-kind="subject"][data-state="comingUp"]').first()).toBeVisible();
  await expect(page.locator("[data-period]").filter({ hasText: "general_awareness" })).toHaveCount(0);
  await expect(page.locator("[data-next]")).toContainText("Coming up");
  await expect(page.getByLabel("What the colours mean").locator("[data-chip]")).toHaveCount(5);
  await tapsAreBig(page);
  await displayFaceOnlyLarge(page);
  await shoot(page, "1-today");
  await page.getByRole("link", { name: "Next day" }).click();
  await expect(page).toHaveURL(/day=2026-11-24/);
  await expect(page.locator('[data-ux="empty"]')).toContainText("Holiday");
  await page.getByRole("link", { name: "Previous day" }).click();
  await expect(page).toHaveURL(/day=2026-11-23/);
  await page.getByRole("link", { name: "Previous day" }).click();
  await expect(page).toHaveURL(/day=2026-11-20/); // a Friday: weekends are skipped
});

test("This week is a grid: a column a day, a row a period, a holiday one cell; on a phone the days stand one under another", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator/week?class=${klass}&day=${MONDAY}`);
  await expect(page.locator("[data-day-head]")).toHaveCount(5);
  await expect(page.locator(`[data-day="${MONDAY}"] [data-period]`)).toHaveCount(15);
  await expect(page.locator('[data-day="2026-11-24"][data-day-kind="holiday"]')).toContainText("Holiday");
  await expect(page.locator('[data-day="2026-11-26"] [data-kind="empty"]').first()).toContainText("Free");
  const y = async (day: string, time: string) => (await page.locator(`[data-day="${day}"] [data-period]`).filter({ hasText: time }).first().boundingBox())!.y;
  expect(Math.round(await y(MONDAY, "09:40"))).toBe(Math.round(await y("2026-11-25", "09:40"))); // one row, one time
  await tapsAreBig(page);
  await displayFaceOnlyLarge(page);
  await shoot(page, "2-week");
  await page.setViewportSize({ width: 390, height: 900 });
  const mondayLast = (await page.locator(`[data-day="${MONDAY}"] [data-period]`).last().boundingBox())!;
  const tuesdayHead = (await page.locator('[data-day-head="2026-11-24"]').boundingBox())!;
  expect(tuesdayHead.y).toBeGreaterThan(mondayLast.y); // stacked
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.locator('[data-day-head="2026-11-25"]').click();
  await expect(page).toHaveURL(/\/educator\?class=.*day=2026-11-25/);
});

test("any block opens its period: the time, the school's words, the planner's lines for the subject, and its activity", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator?class=${klass}&day=${MONDAY}`);
  await page.locator('[data-period]').filter({ hasText: "General Awareness" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Academic 2 General Awareness");
  await expect(page.locator('[data-ux="action"]')).toContainText("10:20–10:40");
  await expect(page.locator('[data-part="school-words"]')).toContainText("Insects");
  await expect(page.locator('[data-part="activity"]')).toContainText("Insects");
  await expect(page.locator('[data-part="planner"] li').first()).toBeVisible();
  await tapsAreBig(page);
  await displayFaceOnlyLarge(page);
  await shoot(page, "3-period");
  await page.getByRole("navigation", { name: "Where you are" }).getByRole("link", { name: "Today" }).click();
  await expect(page).toHaveURL(/\/educator\?class=.*day=2026-11-23/);
});

test("her menu is a sidebar on a desktop and tabs at the foot of a phone, each with where she is marked", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator/week?class=${klass}&day=${MONDAY}`);
  const side = page.locator('[data-educator-nav="side"]');
  await expect(side).toBeVisible();
  await expect(side.locator('[data-nav="week"]')).toHaveAttribute("aria-current", "page");
  await side.locator('[data-nav="week-next"]').click();
  await expect(page.locator("[data-week]")).toHaveAttribute("data-week", /^\d{4}-\d{2}-\d{2}$/);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(`/educator?class=${klass}&day=${MONDAY}`);
  await expect(side).toBeHidden();
  const tabs = page.locator('[data-educator-nav="tabs"]');
  await expect(tabs).toBeVisible();
  await expect(tabs.locator('[data-tab="today"]')).toHaveAttribute("aria-current", "page");
  await tabs.locator('[data-tab="week"]').click();
  await expect(page).toHaveURL(/\/educator\/week/);
});
