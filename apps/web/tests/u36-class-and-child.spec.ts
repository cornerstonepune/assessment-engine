/**
 * U36 — a class and a child, said once (goals/ux4-class-and-child.yaml). Nimish, 2026-10-15: "Most of the pages just
 * have a long list for no reason. All these things should be expandable and collapsible. They should have the right set
 * of columns which are important." And, 2026-09-30, where the colours cannot say yet: "we should have a clear
 * recommendation around the next set of assessments".
 *
 * A Grade 2 class of the test's own. Its children's skill states are set here directly, as tests/u21 does — the graph's
 * own rules are proved by the engine's tests; this is how the pages lay them out — and taken away after:
 * - Asha needs help on 2-digit − 2-digit, is secure on 2-digit + 2-digit and on tallies;
 * - Bina has one answer on 2-digit + 2-digit, too few to say;
 * - Chetan has nothing at all;
 * - Dev has nothing checked, and a class assessment made for him that waits to be read;
 * - Ela has nothing checked, and two papers made for her waiting.
 */
import { expect, test, type Locator, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U36-CLASS";
const DEVS = "CSD36D01";
const ELAS = ["CSE1A001", "CSE1A002"];
let kids: Record<string, string> = {};
const STATES: [string, string, string, string, number, number][] = [
  ["Asha", "R24", "NUM.OPS.02", "patterned_error", 6, 2],
  ["Asha", "R22", "NUM.OPS.01", "secure", 10, 10],
  ["Asha", "R34", "NUM.DATA.01", "secure", 8, 8],
  ["Bina", "R22", "NUM.OPS.01", "not_enough_yet", 1, 1],
];

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan", "Dev", "Ela"]);
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select tenant_id from child where id = ${kids.Asha}`;
  await sql`delete from child_skill_state where child_id in ${sql(Object.values(kids))}`;
  for (const [who, rung, skill, state, n, right] of STATES) {
    await sql`
      insert into child_skill_state (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, last_seen)
      values (${tenant_id}, ${kids[who]}, ${skill}, ${rung}, ${state}, ${n}, ${right}, now())`;
  }
  // Dev's class assessment, approved and printed, not read yet
  const [w] = await sql<{ id: string }[]>`
    select id from sheet_template where source = 'library' and retired_at is null and band = 'G2' order by code limit 1`;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, kind, print_status, approved_by, approved_at)
    select ${tenant_id}, ${DEVS}, ${w.id}, ${kids.Dev}, 'assessment', 'printed', 'u36', now()
    where not exists (select 1 from sheet_instance where qr_code = ${DEVS})`;
  for (const qr of ELAS) {
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, kind, print_status)
      select ${tenant_id}, ${qr}, ${w.id}, ${kids.Ela}, 'practice', 'new'
      where not exists (select 1 from sheet_instance where qr_code = ${qr})`;
  }
});
test.afterAll(async () => {
  await sql`delete from child_skill_state where child_id in ${sql(Object.values(kids))}`;
  await sql.end();
});

/** Every table on the page whose rows are the class's children: where the page says how each child stands. */
const standing = (page: Page) => page.getByRole("main").locator("table:has(tbody tr[data-child])");

/** Each link and button the page shows, as a box: an action off the screen's right edge is one a person never finds. */
async function offScreen(scope: Locator, width: number): Promise<string[]> {
  const actions = scope.locator("a:visible, button:visible, summary:visible");
  const off: string[] = [];
  for (const a of await actions.all()) {
    const box = await a.boundingBox();
    if (box && box.x + box.width > width) off.push((await a.innerText()).trim());
  }
  return off;
}

test("a class shows its standing once: by topic, or one topic's skills in its place", async ({ page }) => {
  await page.goto(`/growth/class/${SECTION}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(SECTION);
  await expect(page.getByRole("main").locator("header")).toContainText("Grade 2");
  // by topic: the one table of where each child stands
  const byTopic = page.getByRole("table", { name: `${SECTION}: each child on each topic` });
  await expect(byTopic).toBeVisible();
  await expect(standing(page)).toHaveCount(1);
  await expect(page.getByRole("table", { name: `${SECTION}: each child on each step` })).toHaveCount(0);

  // a topic opens its skills in the same place, and the topics give way to them
  await byTopic.getByRole("link", { name: "Addition & subtraction", exact: true }).click();
  await expect(page).toHaveURL(/[?&]topic=ADDSUB\b/);
  const steps = page.getByRole("table", { name: `${SECTION}: each child on each step` });
  await expect(steps).toBeVisible();
  await expect(standing(page)).toHaveCount(1);
  const cols = await steps.locator("thead th[data-col]").evaluateAll((ths) => ths.map((t) => t.getAttribute("data-col")));
  expect(cols.sort()).toEqual(["NUM.OPS.01|R22", "NUM.OPS.02|R24"]);

  // one click back to every topic
  const topics = page.getByRole("navigation", { name: "Topic" });
  await expect(topics.getByRole("link", { name: "Addition & subtraction", exact: true })).toHaveAttribute("aria-current", "page");
  await topics.getByRole("link", { name: "All topics" }).click();
  await expect(page).not.toHaveURL(/topic=/);
  await expect(byTopic).toBeVisible();
  await expect(standing(page)).toHaveCount(1);
});

test("every check is one line, its names folded, and every action is on screen", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`/growth/class/${SECTION}`);
  const checks = page.getByRole("region", { name: "Checks that would place them" });
  await expect(checks).toBeVisible();
  // 2-digit + 2-digit: Bina has one answer, Chetan, Dev and Ela none; Asha is secure on it and is not in it
  const add = checks.locator('[data-check="ADD.2D2D"]');
  await expect(add).toHaveCount(1);
  await expect(add).toContainText("4 children");
  await expect(add).toContainText(/\d+ questions · (Easy|Medium|Hard|Advance)/);
  const bina = add.getByText("Bina (1 answer)");
  await expect(bina).toBeHidden();
  await add.locator("summary").click();
  await expect(bina).toBeVisible();
  await expect(add).toContainText("Chetan (none)");
  await expect(add).toContainText("Dev (none)");
  await expect(add).toContainText("Ela (none)");
  await expect(add).not.toContainText("Asha");

  // the skills no child has answered: one folded line, its count the lines inside it
  const none = checks.locator("details[data-unanswered]");
  await expect(none).toHaveCount(1);
  await expect(none).not.toHaveAttribute("open", "");
  await expect(none.locator("> summary")).toBeVisible();
  const said = (await none.locator("> summary").innerText()).match(/^(\d+) skills? no child has answered yet/);
  expect(said, "the fold says how many skills it holds").not.toBeNull();
  await expect(none.locator("[data-check]")).toHaveCount(Number(said![1]));

  // the key is one line, and nothing the page offers is past its right edge
  await expect(page.locator("details[data-colour-key]")).toHaveCount(1);
  expect(await offScreen(page.getByRole("main"), 1280)).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1280);

  // on a phone, each check's button is on screen too
  await page.setViewportSize({ width: 400, height: 860 });
  await page.goto(`/growth/class/${SECTION}`);
  await expect(checks).toBeVisible();
  expect(await offScreen(checks, 400)).toEqual([]);
});

test("a child's page says their standing once, topic by topic, the ones that need help open", async ({ page }) => {
  await page.goto(`/growth/${kids.Asha}`);
  await expect(page.getByTestId("summary")).toHaveText(/^Asha needs help on 1 skill and has got 2;/);
  const shown = page.getByRole("region", { name: "What their answers show" });
  // read once the page has streamed in: no tiles, no second table
  await expect(shown).toBeVisible();
  await expect(page.getByRole("table", { name: "By topic" })).toHaveCount(0);
  await expect(page.getByRole("main").getByText("too few answers yet", { exact: true })).toHaveCount(0);

  const topic = (code: string) => shown.locator(`details[data-topic="${code}"]`);
  // Addition & subtraction holds a skill that needs help: open, its line counting its skills
  await expect(topic("ADDSUB")).toHaveAttribute("open", "");
  await expect(topic("ADDSUB").locator("> summary")).toContainText(/1 needs help\b.*1 secure\b.*\d+ not assessed yet/);
  const list = shown.getByRole("list", { name: "Addition & subtraction" });
  await expect(list).toBeVisible();
  const lines = list.locator(":scope > li");
  expect(await lines.evaluateAll((els) => els.map((e) => e.getAttribute("data-rag")))).toEqual(["red", "green"]);
  // Data handling is all secure: closed, and one click opens it
  await expect(topic("DATA")).not.toHaveAttribute("open", "");
  await expect(topic("DATA").locator("> summary")).toContainText("1 secure");
  await expect(topic("DATA").locator("li[data-skill]")).toBeHidden();
  await topic("DATA").locator("> summary").click();
  await expect(topic("DATA").locator("li[data-skill]")).toBeVisible();
  // the key, one line
  await expect(page.locator("details[data-colour-key]")).toHaveCount(1);
  // nothing runs past its panel's edge: the parent report's state was a pill, which does not wrap
  await expect(page.getByRole("region", { name: "Parent report" })).toBeVisible();
  const over = await page.getByRole("main").getByRole("region").evaluateAll((els) =>
    els.filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.getAttribute("aria-label")),
  );
  expect(over).toEqual([]);
});

test("a child with no answers gets one sentence and one action", async ({ page }) => {
  await page.goto(`/growth/${kids.Chetan}`);
  const sentence = page.getByTestId("summary");
  await expect(sentence).toHaveText(/^Chetan has no checked answers yet: a first check of \d+ questions on each of .+ shows where Chetan stands\.$/);
  const main = page.getByRole("main");
  // nothing else: no panel, and one action beside the way back
  await expect(main.getByRole("region")).toHaveCount(0);
  const actions = main.locator("a:not(nav a), button:not(nav button)");
  await expect(actions).toHaveCount(1);
  const first = main.getByRole("link", { name: "Make Chetan’s first check →" });
  await expect(first).toBeVisible();
  // the check is Chetan's alone, each skill it names one of its lines
  const q = new URL((await first.getAttribute("href"))!, "http://x").searchParams;
  expect([q.getAll("c"), q.get("kind")]).toEqual([[kids.Chetan], "assessment"]);
  const lines = q.getAll("a");
  expect(lines.length).toBeGreaterThanOrEqual(1);
  expect(lines.length).toBeLessThanOrEqual(3);
  const names = await sql<{ name: string }[]>`select name from skill_set where code in ${sql(lines.map((a) => a.split("~")[0]))}`;
  for (const { name } of names) await expect(sentence).toContainText(name);
  await first.click();
  await expect(page).toHaveURL(/\/papers\/make\?/);
  const plan = page.getByRole("table", { name: "Each child's paper" });
  await expect(plan.locator("tbody tr")).toHaveCount(1);
  await expect(plan.locator(`tr[data-child="${kids.Chetan}"]`)).toBeVisible();

  // a paper already made for the child, waiting to be read, is the one action: no second check
  await page.goto(`/growth/${kids.Dev}`);
  await expect(sentence).toHaveText(`Dev has no checked answers yet: class assessment ${DEVS} waits to be read.`);
  await expect(main.getByRole("region")).toHaveCount(0);
  await expect(actions).toHaveCount(1);
  await expect(main.getByRole("link", { name: `Open paper ${DEVS} →` })).toHaveAttribute("href", `/worksheets/${DEVS}`);

  // several waiting: the one action is every one of them, on Assessments
  await page.goto(`/growth/${kids.Ela}`);
  await expect(sentence).toHaveText(`Ela has no checked answers yet: 2 papers made for Ela wait to be approved or read.`);
  await expect(main.getByRole("region")).toHaveCount(0);
  await expect(actions).toHaveCount(1);
  await expect(main.getByRole("link", { name: "See Ela’s 2 papers →" })).toHaveAttribute("href", `/papers?child=${kids.Ela}`);
});
