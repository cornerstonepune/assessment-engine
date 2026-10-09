/**
 * The whole dashboard, driven the way a teacher drives it, against the real database.
 *
 * Every test here does the thing and then proves the thing happened — a click that leaves the
 * database unchanged is a broken button, however green the screen looks. Nothing is mocked and
 * nothing is seeded behind the app's back except the one skill set these tests edit and restore.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";
import { libraryOf, restoreLibrary } from "./library-state";
import { existsSync } from "node:fs";
import path from "node:path";

// These share real rows, so they run in order rather than racing each other.
test.describe.configure({ mode: "serial" });

if (!process.env.DATABASE_URL) {
  const root = path.resolve(process.cwd(), "../../.env");
  if (existsSync(root)) process.loadEnvFile(root);
}
// The local copy (playwright.config.ts refuses any other address), which runs without TLS.
const sql = postgres(process.env.DATABASE_URL!, { max: 2, prepare: false });

/** Everything these tests create carries this note, so it can always be found again. */
const MARK = "end-to-end test";

/**
 * A per-test `finally` is not enough: a server action redirects, and its write can land after the
 * test that triggered it has already failed and cleaned up. One run left a real question retired
 * in the live bank that way. This sweep runs last, after every write has certainly landed.
 */
// What the database already held before a line of this ran. A test can only be blamed for what it
// changed: 93 items were retired on 2026-09-19 by the bank's own review, and a sweep that asserts
// "no item anywhere is retired" calls that dirt. It had never fired — the serial run always failed
// earlier — so the false assertion sat unseen behind a real one.
let retiredBefore = 0;

test.beforeAll(async () => {
  [{ retired: retiredBefore }] = await sql<{ retired: number }[]>`
    select count(*)::int as retired from item where status = 'retired'`;
});

test.afterAll(async () => {
  // A correction's note is "Corrected as <key>: <reason>", so match the mark anywhere in it, and take
  // back the corrected question a test made before bringing the original back.
  const marked = `%${MARK}%`;
  await sql`delete from item where corrected_from in (select item_id from item_feedback where note like ${marked})`;
  await sql`update item set status = 'active' where id in (
    select item_id from item_feedback where note like ${marked})`;
  await sql`delete from item_feedback where note like ${marked}`;
  const [{ leaked }] = await sql<{ leaked: number }[]>`
    select count(*)::int as leaked from item_feedback where note like ${marked}`;
  const [{ retired }] = await sql<{ retired: number }[]>`
    select count(*)::int as retired from item where status = 'retired'`;
  await sql.end();
  if (leaked || retired > retiredBefore) {
    throw new Error(
      `the tests left the database dirty: ${leaked} flags, ` +
        `${retired - retiredBefore} items retired that were not retired before`,
    );
  }
});

// ---------------------------------------------------------------- the menu

test("a teacher can reach every section from the menu, and the menu says where they are", async ({ page }) => {
  await page.goto("/");
  const sections = [
    ["Today", "Today"],
    ["Children", "Children"],
    ["Papers", "Papers"],
    ["Curriculum", "Curriculum"],
  ];
  for (const [label, heading] of sections) {
    await page.getByRole("navigation").getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(page.getByRole("navigation").getByRole("link", { name: label, exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );
  }
});

// ---------------------------------------------------------------- skill map

/** A skill's row in the Curriculum's table (U12), everything opened; `grade` is the grade that holds the level read. */
async function openSkill(page: Page, grade: string, code: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "Open everything" }).click();
  const row = page.getByRole("table", { name: "The curriculum, grade by grade" }).locator(`tr[data-row="${grade}/${code}"]`);
  await expect(row).toBeVisible();
  return row;
}

const hardOf = async () =>
  (
    await sql<{ n: number; outcome: string; grade: string }[]>`
      select count(*)::int as n, (select learning_objective from skill_set where code = 'SUB.2D2D') as outcome,
             (select coalesce(s.level_band ->> 'Hard', r.band) from skill_set s
                join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code where s.code = 'SUB.2D2D') as grade
      from item where status = 'active' and skill_set_code = 'SUB.2D2D' and difficulty = 'Hard'`
  )[0];

test("the skill map's counts are the real number of questions in the bank", async ({ page }) => {
  const { n, grade } = await hardOf();
  const hard = (await openSkill(page, grade, "SUB.2D2D")).locator('td[data-level="Hard"]');
  await expect(hard).toHaveText(n.toLocaleString("en-IN"));
});

test("a count on the skill map opens exactly those questions", async ({ page }) => {
  const { n, grade } = await hardOf();
  const hard = (await openSkill(page, grade, "SUB.2D2D")).locator('td[data-level="Hard"]');
  await hard.getByRole("link", { name: n.toLocaleString("en-IN") }).click();
  await expect(page).toHaveURL(/set=SUB\.2D2D&difficulty=Hard/);
  await expect(page.locator("#questions tbody tr")).toHaveCount(Math.min(n, 50));
});

test("a skill on the map opens its own page", async ({ page }) => {
  const { outcome, grade } = await hardOf();
  await (await openSkill(page, grade, "SUB.2D2D")).getByRole("link", { name: outcome, exact: true }).click();
  await expect(page).toHaveURL(/skill-sets\/SUB\.2D2D/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(outcome);
});

// ---------------------------------------------------------------- approving a skill

test("approving a skill records who did it, by name", async ({ page }) => {
  const [before] = await sql`select status, ratified_by from skill_set where code = 'ADD.3D3D'`;
  try {
    // The test makes its own starting state. Status alone changes no content, so the versioning
    // trigger does not fire.
    await sql`update skill_set set status = 'draft', ratified_by = null where code = 'ADD.3D3D'`;
    await page.goto("/skill-sets/ADD.3D3D");
    await page.getByRole("button", { name: "Approve as written" }).click();
    await expect(page.getByRole("status")).toContainText("Approved as written");
    const [after] = await sql<{ status: string; ratified_by: string }[]>`
      select status, ratified_by from skill_set where code = 'ADD.3D3D'`;
    expect(after.status).toBe("ratified");
    expect(after.ratified_by).toBe("End-to-end test");
  } finally {
    await sql`update skill_set set status = ${before.status}, ratified_by = ${before.ratified_by}
              where code = 'ADD.3D3D'`;
  }
});

// ---------------------------------------------------------------- the question bank

test("the bank's grid holds exactly what the database holds, and a cell opens those questions", async ({ page }) => {
  const [{ total, n, name }] = await sql<{ total: number; n: number; name: string }[]>`
    select (select count(*)::int from item where status = 'active' and source = 'generated' and exists (select 1 from skill_set s join topic t on t.code = s.topic_code and t.taught where s.code = item.skill_set_code)) as total,
           (select count(*)::int from item where status = 'active' and source = 'generated'
              and skill_set_code = 'SUB.2D2D' and difficulty = 'Hard') as n,
           (select name from skill_set where code = 'SUB.2D2D') as name`;
  await page.goto("/library");
  await expect(page.getByText(`${total.toLocaleString("en-IN")} questions ready to print`)).toBeVisible();
  const cell = page.getByRole("link", { name: `${name}, Hard: ${n} questions` });
  await expect(cell).toHaveText(n.toLocaleString("en-IN"));
  await cell.click();
  await expect(page).toHaveURL(/set=SUB\.2D2D/);
  await expect(page.locator("#questions tbody tr")).toHaveCount(Math.min(n, 50));
});

test("every question in the list shows its answer and opens its own page", async ({ page }) => {
  await page.goto("/library?set=SUB.2D2D&difficulty=Hard");
  const rows = page.locator("#questions tbody tr");
  for (const row of (await rows.all()).slice(0, 5)) {
    await expect(row.locator("td").nth(1)).toHaveText(/\d+/); // the answer
  }
  await rows.first().locator("td").first().getByRole("link").click();
  await expect(page).toHaveURL(/\/library\/[A-Za-z0-9._-]+$/);
});

// Twelve kinds of question, each drawn its own way. Before this, eight of them came out as
// "undefined + undefined" because the screen only knew four. A tally's numbers are its drawing, not
// digits (components/pictures.tsx), so the drawing's label is read with the words: a number missing
// from either says undefined or NaN.
test("every kind of question in the bank is drawn with its own numbers", async ({ page }) => {
  const kinds = await sql<{ fmt: string }[]>`
    select distinct fmt from item where status = 'active' and source = 'generated' and exists (select 1 from skill_set s join topic t on t.code = s.topic_code and t.taught where s.code = item.skill_set_code) order by fmt`;
  for (const { fmt } of kinds) {
    await page.goto(`/library?fmt=${fmt}`);
    const question = page.locator("#questions tbody tr").first().locator("td").first();
    const shown = async () => {
      const drawn = await question.locator("svg[aria-label]").evaluateAll((svgs) => svgs.map((s) => s.getAttribute("aria-label")));
      return [await question.textContent(), ...drawn].join(" ");
    };
    await expect.poll(shown, fmt).toMatch(/\d/);
    await expect.poll(shown, fmt).not.toMatch(/undefined|null|NaN/);
  }
});

// A mistake's name depends on the operation: in a subtraction, M_WRONG_OP is "added instead of
// subtracting". The old lookup gave every question the same, arbitrary one of three names.
test("a mistake is named for the question's own operation", async ({ page }) => {
  const [q] = await sql<{ item_key: string }[]>`
    select item_key from item i where status = 'active' and source = 'generated' and spec ->> 'op' = '-'
      and exists (select 1 from jsonb_array_elements(i.responses) r where r -> 'misconceptions' ? 'M_WRONG_OP')
    order by item_key limit 1`;
  await page.goto(`/library/${q.item_key}`);
  const caught = page.getByRole("table", { name: "Wrong answers it catches" });
  await expect(caught).toContainText("Added instead of subtracting");
  await expect(caught).not.toContainText("instead of multiplying");
  await expect(caught).not.toContainText("Subtracted instead of adding");

  // A number wall records no operation: it may not borrow a subtraction's example either.
  const [wall] = await sql<{ item_key: string }[]>`
    select item_key from item where status = 'active' and fmt = 'number_wall' order by item_key limit 1`;
  await page.goto(`/library/${wall.item_key}`);
  await expect(page.getByRole("table", { name: "Wrong answers it catches" })).not.toContainText("difference");
});

// One question, everything about it: the block exactly as it prints, the answer, and every wrong
// answer it catches — the list shows none of that, so nothing can hide behind "+4 more".
test("a question's page shows it as printed, its answer, and every wrong answer it catches", async ({ page }) => {
  const [q] = await sql<{ item_key: string; n: number; answer: string }[]>`
    select item_key, responses -> 0 ->> 'answer' as answer,
           (select count(*)::int from jsonb_array_elements(i.responses) r, jsonb_object_keys(r -> 'misconceptions')) as n
    from item i where status = 'active' and source = 'generated' and fmt = 'word_2step'
    order by item_key limit 1`;
  await page.goto(`/library/${q.item_key}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Two-step word problem");
  const printed = page.getByRole("img", { name: "The question as it prints on a paper" });
  await expect.poll(() => printed.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  await expect(page.getByText(q.answer, { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("table", { name: "Wrong answers it catches" }).locator("tbody tr")).toHaveCount(q.n);

  await page.setViewportSize({ width: 400, height: 860 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, "page must not scroll sideways on a phone").toBeLessThanOrEqual(1);
});

// A teacher rewords a question; the engine keeps its numbers, so the answer cannot change. The new
// wording is a new question, the old one retires naming who and why, and a changed number is refused.
test("correcting a question's wording saves a new question and retires the old one", async ({ page }) => {
  const [q] = await sql<{ id: string; item_key: string; stem: string; skill_set_code: string; difficulty: string }[]>`
    select id, item_key, stem, skill_set_code, difficulty from item
    where status = 'active' and source = 'generated' and fmt = 'word_1step' order by item_key desc limit 1`;
  const reworded = `Read carefully. ${q.stem}`;
  const worksheets = await libraryOf(sql, q.skill_set_code, q.difficulty);
  try {
    await page.goto(`/library/${q.item_key}`);
    const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Save correction" }) });

    await form.locator('textarea[name="stem"]').fill(`${q.stem} There are 98765 more.`);
    await form.locator('input[name="reason"]').fill(MARK);
    await form.getByRole("button", { name: "Save correction" }).click();
    // Both answers come from the engine, which may still be cutting the scan images earlier tests asked
    // for; give it the time a busy engine takes, not a fixed five seconds.
    await expect(page.getByRole("status")).toContainText("Keep every number exactly as it was", { timeout: 15_000 });
    const [{ made }] = await sql<{ made: number }[]>`select count(*)::int as made from item where corrected_from = ${q.id}`;
    expect(made, "a refused correction changes nothing").toBe(0);

    await form.locator('textarea[name="stem"]').fill(reworded);
    await form.locator('input[name="reason"]').fill(MARK);
    await Promise.all([page.waitForURL(/corrected=1/), form.getByRole("button", { name: "Save correction" }).click()]);
    await expect(page.getByRole("status")).toContainText("Saved", { timeout: 15_000 });
    await expect(page.getByText("Reworded by a teacher")).toBeVisible();

    const [row] = await sql<{ status: string; stem: string; same: boolean }[]>`
      select n.status, n.stem, (n.spec = o.spec and n.responses = o.responses) as same
      from item n join item o on o.id = n.corrected_from where o.id = ${q.id}`;
    expect(row).toEqual({ status: "active", stem: reworded, same: true });
    const [old] = await sql<{ status: string }[]>`select status from item where id = ${q.id}`;
    expect(old.status).toBe("retired");
  } finally {
    // The worksheets first: a new one holds the corrected question this puts away.
    await restoreLibrary(sql, q.skill_set_code, q.difficulty, worksheets);
    await sql`delete from item_exposure where item_id in (select id from item where corrected_from = ${q.id})`;
    await sql`delete from item where corrected_from = ${q.id}`;
    await sql`update item set status = 'active' where id = ${q.id}`;
    await sql`delete from item_feedback where item_id = ${q.id} and note like ${`%${MARK}%`}`;
  }
});

test("removing a question retires it in the database and it stops being offered", async ({ page }) => {
  const levels = ["Easy", "Medium", "Hard", "Advance"];
  const worksheets = await Promise.all(levels.map((d) => libraryOf(sql, "SUB.2D2D", d)));
  try {
    await page.goto("/library?set=SUB.2D2D");
    await page.locator("#questions tbody tr").first().locator("td").first().getByRole("link").click();
    await page.locator('input[name="note"]').fill(MARK);
    await page.getByRole("button", { name: "Remove this question" }).click();
    await expect(page.getByRole("status")).toContainText("It will not print again");

    // The flag is recorded with who said it and why …
    await expect
      .poll(async () => {
        const [{ n }] = await sql<{ n: number }[]>`
          select count(*)::int as n from item_feedback where note = ${MARK} and verdict = 'retire'`;
        return n;
      })
      .toBeGreaterThan(0);
    // … and the database trigger retires the question, so it can never print again.
    const [retired] = await sql<{ status: string; actor: string }[]>`
      select i.status, f.actor from item i join item_feedback f on f.item_id = i.id
      where f.note = ${MARK} limit 1`;
    expect(retired.status).toBe("retired");
    expect(retired.actor).toBeTruthy();
  } finally {
    for (const [i, d] of levels.entries()) await restoreLibrary(sql, "SUB.2D2D", d, worksheets[i]);
    await sql`update item set status = 'active' where id in (
      select item_id from item_feedback where note = ${MARK})`;
    await sql`delete from item_feedback where note = ${MARK}`;
  }
});

// ---------------------------------------------------------------- the screens with no data yet

test("a screen with no data says what it will show and the real count today", async ({ page }) => {
  // The list is what is still a placeholder, and it shrinks as screens get built: `/capture` is
  // the approval screen now and `/growth` is a child's ladder. This assertion had not actually run
  // since either was built — the serial run always failed earlier and skipped it.
  for (const [route, table] of [["/home", "home sheets"]]) {
    await page.goto(route);
    await expect(page.getByText("What this screen will show")).toBeVisible();
    await expect(page.getByText("In the database today")).toBeVisible();
    await expect(page.getByRole("table")).toContainText(table);
  }
});

