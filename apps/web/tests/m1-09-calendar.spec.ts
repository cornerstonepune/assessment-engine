/**
 * M1-09 — the K2 educator's Today and This week as calendars (goals/m1-09c-educator-calendar.yaml, D-075, D-076), on
 * M1-06's /timetable routes with Fortnight 10 as the school wrote it, loaded by M1-06's own loader into the tests'
 * placeholder K2 class (M1-06's `engine timetable load`). Every period a block with its time as time and the
 * school's words, coloured by its state; every block opens its period. No child anywhere.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { displayFaceOnlyLarge, loadFortnight10, shoot, tapsAreBig, timetableSwitch } from "./educator-screens";
import { SECTION, k2Class } from "./k2-rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MONDAY = "2026-11-23"; // Fortnight 10, week A; Tuesday 24 is a holiday
let klass = "";

test.beforeAll(async () => {
  ({ klass } = await k2Class(sql));
  loadFortnight10(SECTION);
});
test.afterAll(async () => {
  await timetableSwitch(sql, false);
  await sql.end();
});

const white = (page: Page) => page.locator("[data-educator]").evaluate((e) => getComputedStyle(e).backgroundColor);

test("a day in the address that is not a date is not found, never an error", async ({ page }) => {
  await timetableSwitch(sql, true);
  for (const href of ["/educator?day=foo", "/educator?day=foo&go=tomorrow", "/educator/week?day=foo"]) {
    await page.goto(`${href}&class=${klass}`);
    await expect(page.getByText("This page could not be found.")).toBeVisible();
  }
});

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
  // no chip but Do now on any cell (D-075: a future cell has none, and nothing is recorded); Do now only while it runs
  await expect(page.locator(`[data-day="${MONDAY}"] [data-chip]:not([data-chip="doNow"])`)).toHaveCount(0);
  const fills = await page.locator("[data-educator] *").evaluateAll((els) =>
    els.map((e) => getComputedStyle(e).backgroundColor).filter((c) => ["rgb(243, 241, 232)", "rgb(251, 250, 247)", "rgb(237, 227, 211)"].includes(c)),
  );
  expect(fills, "no sand, ivory or cream fill").toEqual([]);
  const strip = page.locator("[data-summary]");
  await expect(strip).toContainText("15 periods");
  await expect(strip.locator("a").first()).toBeVisible(); // every count opens what it counts
  await expect(page.locator("[data-period]").filter({ hasText: "general_awareness" })).toHaveCount(0);
  const ahead = MONDAY > (await page.evaluate(() => new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" })));
  await expect(page.locator("[data-next]")).toContainText(ahead ? "09:40" : "This day is over."); // on and after the day itself, the aside says so
  await expect(page.getByLabel("What the colours mean").locator("[data-chip]")).toHaveCount(4); // Do now, Coming up, Done, Late
  await expect(page.locator("[data-now]")).toHaveCount(0); // not today: no Now line
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
  await expect(page.locator(`[data-day="${MONDAY}"] [data-period]`).first()).toBeVisible(); // streamed in: wait for it shown
  const y = async (day: string, time: string) => (await page.locator(`[data-day="${day}"] [data-period]`).filter({ hasText: new RegExp(`^${time}`) }).first().boundingBox())!.y;
  expect(Math.round(await y(MONDAY, "09:40"))).toBe(Math.round(await y("2026-11-25", "09:40"))); // one row, one time
  await tapsAreBig(page);
  await displayFaceOnlyLarge(page);
  await expect(page.locator("[data-summary]")).toContainText("1 holiday");
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
  await expect(page.locator("[data-summary]")).toContainText("1 activity");
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

test("in the week grid today's column is grey and no future cell carries a chip", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator/week?class=${klass}&day=${MONDAY}`);
  await expect(page.locator("[data-week] [data-chip]")).toHaveCount(0);
  await expect(page.locator("[data-today-column]")).toHaveCount(0); // a week not this one: no column is today's
  await page.goto(`/educator/week?class=${klass}`); // this week: today's column is grey
  const today = page.locator("[data-today-column]");
  if (await page.locator('[data-day-head]').count()) {
    const weekday = await page.evaluate(() => new Date().toLocaleDateString("en-GB", { weekday: "short", timeZone: "Asia/Kolkata" }));
    if (!["Sat", "Sun"].includes(weekday)) {
      await expect(today).toHaveCount(1);
      expect(await today.evaluate((e) => getComputedStyle(e).backgroundColor)).not.toBe("rgba(0, 0, 0, 0)");
    }
  }
});

test("the school's tokens load inside the shell only: a page outside it keeps the site's own look", async ({ page }) => {
  await page.goto("/papers");
  const outside = await page.evaluate(() => ({
    token: getComputedStyle(document.documentElement).getPropertyValue("--chip-done-fg").trim(),
    font: getComputedStyle(document.body).fontFamily,
  }));
  expect(outside.token).toBe("");
  expect(outside.font).toMatch(/Source Serif/);
});
