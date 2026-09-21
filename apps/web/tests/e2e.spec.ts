/**
 * The whole dashboard, driven the way a teacher drives it, against the real database.
 *
 * Every test here does the thing and then proves the thing happened — a click that leaves the
 * database unchanged is a broken button, however green the screen looks. Nothing is mocked and
 * nothing is seeded behind the app's back except the one skill set these tests edit and restore.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
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
    ["Worksheets", "Worksheets"],
    ["Question bank", "Question bank"],
    ["Capture & Mark", "Capture & Mark"],
    ["Child Growth", "Child Growth"],
    ["Home Assignments", "Home Assignments"],
    ["Skill Map", "Skill Map"],
  ];
  for (const [label, heading] of sections) {
    await page.getByRole("navigation").getByRole("link", { name: label }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(page.getByRole("link", { name: label })).toHaveAttribute("aria-current", "page");
  }
});

// ---------------------------------------------------------------- skill map

test("the skill map's counts are the real number of questions in the bank", async ({ page }) => {
  await page.goto("/");
  const [{ n, outcome }] = await sql<{ n: number; outcome: string }[]>`
    select count(*)::int as n, (select learning_objective from skill_set where code = 'SUB.2D.EXCH') as outcome
    from item where status = 'active' and skill_set_code = 'SUB.2D.EXCH' and difficulty = 'Hard'`;
  const row = page.getByRole("row").filter({ hasText: outcome });
  await expect(row).toContainText(`${n} questions`);
});

test("a count on the skill map opens exactly those questions", async ({ page }) => {
  const [{ n, name }] = await sql<{ n: number; name: string }[]>`
    select count(*)::int as n, (select name from skill_set where code = 'SUB.2D.EXCH') as name from item
    where status = 'active' and source = 'generated' and skill_set_code = 'SUB.2D.EXCH' and difficulty = 'Hard'`;
  await page.goto("/");
  await page.getByRole("link", { name: `${name}, Hard: ${n} questions` }).click();
  await expect(page).toHaveURL(/set=SUB\.2D\.EXCH&difficulty=Hard/);
  await expect(page.locator("#questions tbody tr")).toHaveCount(Math.min(n, 50));
});

test("a skill on the map opens its own page", async ({ page }) => {
  const [{ outcome }] = await sql<{ outcome: string }[]>`select learning_objective as outcome from skill_set where code = 'SUB.2D.EXCH'`;
  await page.goto("/");
  await page.getByRole("link", { name: outcome }).click();
  await expect(page).toHaveURL(/skill-sets\/SUB\.2D\.EXCH/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(outcome);
});

// ---------------------------------------------------------------- approving a skill

test("approving a skill records who did it, by name", async ({ page }) => {
  const [before] = await sql`select status, ratified_by from skill_set where code = 'ADD.3D.REG'`;
  try {
    // The test makes its own starting state. Status alone changes no content, so the versioning
    // trigger does not fire.
    await sql`update skill_set set status = 'draft', ratified_by = null where code = 'ADD.3D.REG'`;
    await page.goto("/skill-sets/ADD.3D.REG");
    await page.getByRole("button", { name: "Approve as written" }).click();
    await expect(page.getByRole("status")).toContainText("Approved as written");
    const [after] = await sql<{ status: string; ratified_by: string }[]>`
      select status, ratified_by from skill_set where code = 'ADD.3D.REG'`;
    expect(after.status).toBe("ratified");
    expect(after.ratified_by).toBe("End-to-end test");
  } finally {
    await sql`update skill_set set status = ${before.status}, ratified_by = ${before.ratified_by}
              where code = 'ADD.3D.REG'`;
  }
});

// ---------------------------------------------------------------- the question bank

test("the bank's grid holds exactly what the database holds, and a cell opens those questions", async ({ page }) => {
  const [{ total, n, name }] = await sql<{ total: number; n: number; name: string }[]>`
    select (select count(*)::int from item where status = 'active' and source = 'generated') as total,
           (select count(*)::int from item where status = 'active' and source = 'generated'
              and skill_set_code = 'SUB.2D.EXCH' and difficulty = 'Hard') as n,
           (select name from skill_set where code = 'SUB.2D.EXCH') as name`;
  await page.goto("/library");
  await expect(page.getByText(`${total.toLocaleString("en-IN")} questions ready to print`)).toBeVisible();
  const cell = page.getByRole("link", { name: `${name}, Hard: ${n} questions` });
  await expect(cell).toHaveText(n.toLocaleString("en-IN"));
  await cell.click();
  await expect(page).toHaveURL(/set=SUB\.2D\.EXCH/);
  await expect(page.locator("#questions tbody tr")).toHaveCount(Math.min(n, 50));
});

test("every question in the list shows its answer and opens its own page", async ({ page }) => {
  await page.goto("/library?set=SUB.2D.EXCH&difficulty=Hard");
  const rows = page.locator("#questions tbody tr");
  for (const row of (await rows.all()).slice(0, 5)) {
    await expect(row.locator("td").nth(1)).toHaveText(/\d+/); // the answer
  }
  await rows.first().locator("td").first().getByRole("link").click();
  await expect(page).toHaveURL(/\/library\/[A-Za-z0-9._-]+$/);
});

// Twelve kinds of question, each drawn its own way. Before this, eight of them came out as
// "undefined + undefined" because the screen only knew four.
test("every kind of question in the bank is drawn with its own numbers", async ({ page }) => {
  const kinds = await sql<{ fmt: string }[]>`
    select distinct fmt from item where status = 'active' and source = 'generated' order by fmt`;
  for (const { fmt } of kinds) {
    await page.goto(`/library?fmt=${fmt}`);
    const question = page.locator("#questions tbody tr").first().locator("td").first();
    await expect(question, fmt).toHaveText(/\d/);
    await expect(question, fmt).not.toHaveText(/undefined|null|NaN/);
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
  const [q] = await sql<{ id: string; item_key: string; stem: string }[]>`
    select id, item_key, stem from item where status = 'active' and source = 'generated' and fmt = 'word_1step'
    order by item_key desc limit 1`;
  const reworded = `Read carefully. ${q.stem}`;
  try {
    await page.goto(`/library/${q.item_key}`);
    const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Save correction" }) });

    await form.locator('textarea[name="stem"]').fill(`${q.stem} There are 98765 more.`);
    await form.locator('input[name="reason"]').fill(MARK);
    await form.getByRole("button", { name: "Save correction" }).click();
    await expect(page.getByRole("status")).toContainText("Keep every number exactly as it was");
    const [{ made }] = await sql<{ made: number }[]>`select count(*)::int as made from item where corrected_from = ${q.id}`;
    expect(made, "a refused correction changes nothing").toBe(0);

    await form.locator('textarea[name="stem"]').fill(reworded);
    await form.locator('input[name="reason"]').fill(MARK);
    await Promise.all([page.waitForURL(/corrected=1/), form.getByRole("button", { name: "Save correction" }).click()]);
    await expect(page.getByRole("status")).toContainText("Saved");
    await expect(page.getByText("Reworded by a teacher")).toBeVisible();

    const [row] = await sql<{ status: string; stem: string; same: boolean }[]>`
      select n.status, n.stem, (n.spec = o.spec and n.responses = o.responses) as same
      from item n join item o on o.id = n.corrected_from where o.id = ${q.id}`;
    expect(row).toEqual({ status: "active", stem: reworded, same: true });
    const [old] = await sql<{ status: string }[]>`select status from item where id = ${q.id}`;
    expect(old.status).toBe("retired");
  } finally {
    await sql`delete from item where corrected_from = ${q.id}`;
    await sql`update item set status = 'active' where id = ${q.id}`;
    await sql`delete from item_feedback where item_id = ${q.id} and note like ${`%${MARK}%`}`;
  }
});

test("removing a question retires it in the database and it stops being offered", async ({ page }) => {
  try {
    await page.goto("/library?set=SUB.2D.EXCH");
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
    await sql`update item set status = 'active' where id in (
      select item_id from item_feedback where note = ${MARK})`;
    await sql`delete from item_feedback where note = ${MARK}`;
  }
});

// ---------------------------------------------------------------- worksheets

test("a paper opens from its code: the page as printed, how it was drawn, and its whole key", async ({ page }) => {
  const [paper] = await sql<{ qr: string; section: string; week: string; kind: string; n: number; pool: number }[]>`
    select si.qr_code as qr, c.section, p.week, p.kind, array_length(st.item_ids, 1) as n,
           (select count(*)::int from item i where i.status = 'active' and i.source = 'generated'
              and i.skill_set_code = st.skill_set_code and i.difficulty = st.difficulty) as pool
    from prescription p
    join child c on c.id = p.child_id
    join sheet_instance si on si.id = p.sheet_instance_id
    join sheet_template st on st.id = si.sheet_template_id
    where si.pdf_path is not null
    order by si.created_at limit 1`;
  test.skip(!paper, "no rendered paper in this database yet");

  await page.goto(`/worksheets?section=${paper.section}&week=${paper.week}&kind=${paper.kind}`);
  await page.getByRole("link", { name: paper.qr, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Paper ${paper.qr}`);
  await expect(page.getByRole("table", { name: "Answer key" }).locator("tbody tr")).toHaveCount(paper.n);
  await expect(page.getByText(`${paper.n} picked at random from ${paper.pool.toLocaleString("en-IN")}`)).toBeVisible();

  // The page itself, QR and all, comes from the PDF the engine rendered — not a second drawing.
  const printed = page.getByRole("img", { name: `Page 1 of paper ${paper.qr}, as printed` });
  await expect.poll(() => printed.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);

  await page.setViewportSize({ width: 400, height: 860 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, "page must not scroll sideways on a phone").toBeLessThanOrEqual(1);

  // A code that names no paper says so. The status is 200, not 404: the loading screen streams
  // first (app/(app)/loading.tsx), and Next cannot change a status once it has sent it.
  await page.goto("/worksheets/CS000000");
  await expect(page.getByText("This page could not be found.")).toBeVisible();
});

test("the week's plan shows every child with a level and a reason", async ({ page }) => {
  await page.goto("/worksheets");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Worksheets");
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from prescription p join child c on c.id = p.child_id
    where c.section = 'G3' and p.week = 'T2W1' and p.kind = 'practice'`;
  await page.goto("/worksheets?section=G3&week=T2W1&kind=practice");
  const rows = page.getByRole("table").first().locator("tbody tr");
  await expect(rows).toHaveCount(n);
  for (const row of await rows.all()) {
    await expect(row).toContainText(/Easy|Medium|Hard|Advance/);
    await expect(row).toContainText(/level|showed|hand/); // every row explains itself
  }
});

test("every child's paper has its own code, and no two children share questions", async ({ page }) => {
  await page.goto("/worksheets?section=G3&week=T2W1&kind=practice");
  const codes = await page.getByRole("table").first().locator("tbody tr td:nth-child(4)").allInnerTexts();
  const real = codes.filter((c) => /^CS[0-9A-F]{6}$/.test(c.trim()));
  expect(real.length).toBeGreaterThan(0);
  expect(new Set(real).size).toBe(real.length);

  const [{ shared }] = await sql<{ shared: number }[]>`
    select count(*)::int as shared from sheet_template a join sheet_template b
    on a.id < b.id and a.item_ids && b.item_ids
    where a.week = 'T2W1' and b.week = 'T2W1' and a.child_id is not null and b.child_id is not null`;
  expect(shared).toBe(0);
});

test("changing one child's level writes the reason and survives the next prescribe", async ({ page }) => {
  const [before] = await sql<{ id: string; difficulty: string; rule_fired: string }[]>`
    select p.id, p.difficulty, p.rule_fired from prescription p join child c on c.id = p.child_id
    where c.section = 'G3' and p.week = 'T2W1' and c.roll_no = '1'`;
  try {
    await page.goto("/worksheets?section=G3&week=T2W1&kind=practice");
    const row = page.getByRole("table").first().locator("tbody tr").first();
    await row.getByText("Change level").click();
    await row.locator('select[name="difficulty"]').selectOption("Easy");
    await row.locator('input[name="reason"]').fill("she was away all week");
    await row.getByRole("button", { name: "Change this child" }).click();
    await expect(page.getByRole("status")).toContainText("Changed");

    const [after] = await sql<{ difficulty: string; rule_fired: string; override_reason: string }[]>`
      select difficulty, rule_fired, override_reason from prescription where id = ${before.id}`;
    expect(after.difficulty).toBe("Easy");
    expect(after.rule_fired).toBe("override");
    expect(after.override_reason).toBe("she was away all week");
    await expect(page.getByRole("table").first()).toContainText("she was away all week");
  } finally {
    await sql`update prescription set difficulty = ${before.difficulty}, rule_fired = ${before.rule_fired},
              override_by = null, override_reason = null where id = ${before.id}`;
  }
});

test("a level change with no reason is refused and nothing moves", async ({ page }) => {
  const [before] = await sql<{ id: string; difficulty: string }[]>`
    select p.id, p.difficulty from prescription p join child c on c.id = p.child_id
    where c.section = 'G3' and p.week = 'T2W1' and c.roll_no = '2'`;
  await page.goto("/worksheets?section=G3&week=T2W1&kind=practice");
  const row = page.getByRole("table").first().locator("tbody tr").nth(1);
  await row.getByText("Change level").click();
  await row.locator('select[name="difficulty"]').selectOption("Advance");
  await row.getByRole("button", { name: "Change this child" }).click();

  // The browser's own required-field check stops it; the row is untouched either way.
  const [after] = await sql<{ difficulty: string }[]>`select difficulty from prescription where id = ${before.id}`;
  expect(after.difficulty).toBe(before.difficulty);
});

test("approving the pack marks the papers printed", async ({ page }) => {
  // Everything the approval writes is put back, the approver included: a paper that is not printed
  // must not name someone as having approved it.
  const codes = await sql<{ id: string; print_status: string; approved_by: string | null; approved_at: Date | null }[]>`
    select si.id, si.print_status, si.approved_by, si.approved_at from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id where st.week = 'T2W1'`;
  try {
    await page.goto("/worksheets?section=G3&week=T2W1&kind=practice");
    await page.getByRole("button", { name: "Approve and print" }).click();
    await expect(page.getByRole("status")).toContainText("Approved");

    const [{ n }] = await sql<{ n: number }[]>`
      select count(*)::int as n from sheet_instance si join sheet_template st on st.id = si.sheet_template_id
      where st.week = 'T2W1' and si.print_status = 'printed'`;
    expect(n).toBeGreaterThan(0);
    await expect(page.getByRole("table").first()).toContainText("printed");
  } finally {
    for (const c of codes) {
      await sql`update sheet_instance set print_status = ${c.print_status}, printed_at = null,
                approved_by = ${c.approved_by}, approved_at = ${c.approved_at} where id = ${c.id}`;
    }
  }
});

test("spare copies are listed and carry no child's name", async ({ page }) => {
  await page.goto("/worksheets?section=G3&week=T2W1&kind=practice");
  const panel = page.locator("section").filter({ hasText: "Spare copies" });
  await expect(panel).toContainText(/CS[0-9A-F]{6}/);
  const [{ named }] = await sql<{ named: number }[]>`
    select count(*)::int as named from sheet_instance si join sheet_template st on st.id = si.sheet_template_id
    where st.week = 'T2W1' and st.child_id is null and si.child_id is not null`;
  expect(named).toBe(0);
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

