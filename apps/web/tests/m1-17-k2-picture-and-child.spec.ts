/**
 * M1-17 — a K2 child's plan and growth, and the class picture. A child is by Sr. No. alone; the rows are placeholders
 * (the class "M104" of k2-rows.ts, two skills, four children seen). The educator switch is on only inside a test.
 * Walkthrough, taps counted: the class picture (0 taps, the address) → a child (1 tap on the Sr. No.) → back (1 tap).
 */
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { k2Class, voiceSwitch } from "./k2-rows";

const SECTION = "M117";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SHOTS = path.resolve(__dirname, "../../../docs/screens/m1-17");
const DESKTOP = { width: 1280, height: 900 };
const PHONE = { width: 390, height: 844 };
let klass: string;
let staff: string;
let tenant: string;
let skills: { code: string; name: string }[];

async function observe(roll: string, activity: string, level: number | null, daysAgo: number, mode = "individual") {
  const [c] = await sql<{ child_id: string }[]>`select child_id from enrolment where class_id = ${klass} and roll_no = ${roll} and to_date is null`;
  const by = staff; // the tester, who observed and confirmed
  const at = new Date(Date.now() - daysAgo * 86400_000);
  const [o] = await sql<{ id: string }[]>`
    insert into activity_observation (tenant_id, confirmation_id, activity_code, child_id, class_id, outcome, entry_mode, route, expected_level, reached_level, observed_at, observed_by, confirmed_by)
    values (${tenant}, gen_random_uuid(), ${activity}, ${c.child_id}, ${klass}, ${mode === "individual" ? "as_expected" : "as_expected"}, ${mode}, 'form', ${level ?? 2}, ${level}, ${at}, ${by}, ${by}) returning id`;
  if (level !== null || mode !== "individual") {
    const mark = level === 3 ? "yes" : level === 2 ? "sometimes" : "not_yet";
    for (const s of skills.slice(0, 2)) {
      await sql`insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by, kind, mark, seen_by, place, source, observation_id)
        values (${tenant}, ${c.child_id}, ${s.code}, 'educator', ${at}, ${by}, 'observed', ${mark}, ${by}, 'class', 'm1-17 test', ${o.id})`;
    }
  }
  await sql`select rebuild_child_observed_state(${c.child_id})`;
}

async function shoot(page: Page, name: string) {
  for (const [size, at] of [["1280", DESKTOP], ["390", PHONE]] as const) {
    await page.setViewportSize(at);
    await page.locator("[data-ux=action]").waitFor();
    await page.screenshot({ path: path.join(SHOTS, `${name}-${size}.png`), fullPage: true });
  }
  await page.setViewportSize(DESKTOP);
}

test.beforeAll(async () => {
  mkdirSync(SHOTS, { recursive: true });
  ({ klass, staff } = await k2Class(sql, SECTION)); // its own class: other specs leave observations in the shared M104
  [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant order by created_at limit 1`;
  skills = await sql<{ code: string; name: string }[]>`select code, name from registry_skill where tenant_id = ${tenant} order by code limit 4`;
});
test.afterAll(async () => {
  await voiceSwitch(sql, false);
  await sql.end();
});

test("with the educator switch off the pages say so and show no child", async ({ page }) => {
  await voiceSwitch(sql, false);
  await page.goto(`/k2/${klass}`);
  await expect(page.locator("[data-ux=empty]")).toBeVisible();
  await expect(page.locator("[data-k2=grid]")).toHaveCount(0);
  await page.goto(`/k2/${klass}/1`);
  await expect(page.locator("[data-k2=plan]")).toHaveCount(0);
});

test("a class nobody has been seen in is an empty state, not a blank", async ({ page }) => {
  await voiceSwitch(sql, true);
  // a class of its own with no child seen, the tester's grant on it: it is empty on any database, so the test never skips
  const [{ id: empty }] = await sql<{ id: string }[]>`
    insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)
    select tenant_id, campus_id, academic_year_id, grade_code, 'M117E' from school_class where id = ${klass}
    on conflict (tenant_id, campus_id, academic_year_id, grade_code, section) do update set section = excluded.section returning id`;
  await sql`
    insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by)
    select ${tenant}, ${staff}, 'class_teacher', ${empty}, current_date - 1, 'm1-17 test'
    where not exists (select 1 from staff_role_grant where staff_id = ${staff} and school_class_id = ${empty})`;
  await page.goto(`/k2/${empty}`);
  await expect(page.getByText("No child in this class has been seen on a skill yet")).toBeVisible();
  await shoot(page, "class-empty");
});

test("the class picture and a child's page, from the same rows, with taps counted", async ({ page }) => {
  await voiceSwitch(sql, true);
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from activity_observation where class_id = ${klass}`;
  if (n === 0) {
    await observe("1", "ACT-K2-M104-904", 3, 40);
    await observe("1", "ACT-K2-M104-907", 3, 20);
    await observe("2", "ACT-K2-M104-904", 2, 10);
    await observe("3", "ACT-K2-M104-904", 1, 5);
    await observe("4", "ACT-K2-M104-904", null, 5, "group_as_expected");
  }
  let taps = 0;
  const font = () => page.evaluate(() => getComputedStyle(document.body).fontFamily);
  await page.goto("/today");
  const appFont = await font(); // the app's font before any K2 page loads the tokens
  await page.goto(`/k2/${klass}`);
  const grid = page.locator("[data-k2=grid]");
  await expect(grid).toBeVisible();
  // the state in each cell is the database's, in the school's words
  const row1 = grid.locator("tbody tr").filter({ has: page.getByRole("link", { name: "1", exact: true }) });
  await expect(row1.locator("[data-child-state]").first()).toBeVisible();
  // a child not seen has a dash and the words "not yet seen" for a screen reader, never "not secure"
  const row9 = grid.locator("tbody tr").nth(8);
  await expect(row9.locator("[data-seen=no]").first()).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/not secure/i);
  // no terracotta on a child: no chip of the late/missing tone anywhere on the page
  await expect(page.locator("[data-tone=act]")).toHaveCount(0);
  await expect(page.locator("[data-k2=strip] [data-child-state]").first()).toBeVisible();
  // the ground is white; and nothing about these pages changes the app's own font on any page after them
  expect(await page.locator("[data-educator]").evaluate((e) => getComputedStyle(e).backgroundColor)).toBe("rgb(255, 255, 255)");
  // in the school's shell: its sidebar marks Children, and a breadcrumb says where this page is
  await expect(page.locator("[data-educator-nav=side] [data-nav=children]")).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "Where you are" })).toContainText("Children");
  await shoot(page, "class-picture");
  // the page does not scroll sideways at phone width; the grid scrolls inside its own box
  await page.setViewportSize(PHONE);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.setViewportSize(DESKTOP);

  taps += 1;
  await grid.getByRole("link", { name: "1", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/k2/${klass}/1$`));
  await expect(page.locator("[data-k2=plan] [data-child-state]").first()).toBeVisible();
  // growth: a trend in words, the months with their level and days, nothing summed
  const growth = page.locator("[data-k2=growth] li[data-trend]").first();
  await expect(growth).toContainText(/first seen/);
  await expect(growth).toContainText(/level \d of 3/);
  await expect(page.locator("[data-k2=growth]")).not.toContainText(/score|average|total/i);
  await expect(page.locator("body")).not.toContainText(/not ready/i);
  await expect(page.locator("[data-tone=act]")).toHaveCount(0);
  await shoot(page, "child");

  taps += 1;
  await page.getByRole("link", { name: "Class picture" }).first().click();
  await expect(page).toHaveURL(new RegExp(`/k2/${klass}$`));
  expect(taps).toBe(2);
  // leave the K2 pages by a link inside the app: the next page still has the app's font, so the tokens did not leak
  await page.getByRole("link", { name: "Back to what needs doing" }).click();
  await expect(page).toHaveURL(/\/today/);
  expect(await font()).toBe(appFont);
});

test("Children opens from the menu: her classes, one tap to a class's picture, the shell around it", async ({ page }) => {
  await voiceSwitch(sql, true);
  await page.goto("/k2");
  const mine = page.getByRole("list", { name: "Your classes" }).getByRole("link");
  await expect(mine.first()).toBeVisible();
  await page.getByRole("list", { name: "Your classes" }).getByRole("link", { name: /M117$/ }).click();
  await expect(page).toHaveURL(new RegExp(`/k2/${klass}$`));
  await expect(page.locator("[data-educator-nav=side]")).toBeVisible();
  await page.setViewportSize(PHONE); // a phone: the tab bar at the foot, no sidebar
  await expect(page.locator("[data-educator-nav=tabs]")).toBeVisible();
  await page.setViewportSize(DESKTOP);
});

test("a child with nothing ready next is told why, and no skill is called not ready", async ({ page }) => {
  await voiceSwitch(sql, true);
  await page.goto(`/k2/${klass}/2`); // practising only: no skill is done, so no link can make another ready
  await expect(page.locator("[data-k2=ready-next]")).toContainText("only links between skills that a member of staff has confirmed");
  await expect(page.locator("body")).not.toContainText(/not ready/i);
  await shoot(page, "child-nothing-next");
});

test("a confirmed link makes a skill ready next; a proposed one does not", async ({ page }) => {
  await voiceSwitch(sql, true);
  const [a, , c, d] = skills; // child 1 is secure on a (level 3 on two days, 20 days apart); c and d were never seen
  // child 1 is secure on `a`; the engine's own fixture proposes one link and confirms the other (no web code names the raw link tables)
  const engine = path.resolve(__dirname, "../../../packages/engine");
  execFileSync(path.join(engine, ".venv/bin/python"), ["tests/k2_link_fixture.py", a.code, c.code, d.code], { cwd: engine, env: process.env, stdio: "pipe" });
  const [{ state }] = await sql<{ state: string }[]>`select s.state from child_observed_state s join enrolment e on e.child_id = s.child_id
    where e.class_id = ${klass} and e.roll_no = '1' and s.skill_code = ${a.code}`;
  expect(state).toBe("secure");
  await page.goto(`/k2/${klass}/1`);
  const ready = page.locator("[data-k2=ready-next]");
  await expect(ready).toContainText(c.name);
  await expect(ready).toContainText(`after ${a.name}`);
  await expect(ready).not.toContainText(d.name);
  await expect(page.locator("body")).not.toContainText(/not ready/i);
  await shoot(page, "child-ready-next");
});

test("token check: the new screens name no raw colour and no terracotta, and a child's chip has no late tone", async () => {
  const { readFileSync } = await import("node:fs");
  for (const f of ["lib/k2-child.ts", "lib/k2-menu.ts", "components/child-state-chip.tsx", "app/(app)/k2/layout.tsx", "app/(app)/k2/notice.tsx", "app/(app)/k2/page.tsx", "app/(app)/k2/[class]/page.tsx", "app/(app)/k2/[class]/[roll]/page.tsx"]) {
    const text = readFileSync(path.resolve(__dirname, "..", f), "utf8").replace(/^\s*\/\/.*$/gm, ""); // code, not its comments
    expect(text, f).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(text, f).not.toMatch(/terracotta|clay|text-red|bg-red|border-red/);
  }
  const { CHILD_LOOK } = await import("../lib/k2-child");
  expect(Object.values(CHILD_LOOK).map((s) => s.tone as string)).not.toContain("act");
});
