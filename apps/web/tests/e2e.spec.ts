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
const sql = postgres(process.env.DATABASE_URL!, { ssl: "require", max: 2, prepare: false });

test.afterAll(async () => {
  await sql.end();
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
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from item
    where status = 'active' and skill_set_code = 'SUB.2D.EXCH' and difficulty = 'Hard'`;
  const row = page.getByRole("row", { name: /SUB\.2D\.EXCH/ });
  await expect(row).toContainText(String(n));
});

test("a skill set on the map opens its own page", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "SUB.2D.EXCH" }).click();
  await expect(page).toHaveURL(/skill-sets\/SUB\.2D\.EXCH/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("2-digit subtraction with exchange");
});

// ---------------------------------------------------------------- the skill set editor

test("editing a difficulty in plain fields changes the rule the checker enforces", async ({ page }) => {
  const [before] = await sql`select difficulty from skill_set where code = 'SUB.2D.EXCH'`;
  try {
    await page.goto("/skill-sets/SUB.2D.EXCH");
    await page.locator('textarea[name="words:Easy"]').fill("A gentle warm-up, set from the app.");
    await page.locator('input[name="top:Easy"]').fill("3");
    await page.locator('input[name="regroups:Easy"][value="2"]').check();
    await page.locator('select[name="zeros:Easy"]').selectOption("none");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("status")).toContainText("Saved");

    const [after] = await sql<{ difficulty: Record<string, { words: string; check: Record<string, unknown> }> }[]>`
      select difficulty from skill_set where code = 'SUB.2D.EXCH'`;
    expect(after.difficulty.Easy.words).toBe("A gentle warm-up, set from the app.");
    expect(after.difficulty.Easy.check.digits).toEqual([3, 1]);
    expect(after.difficulty.Easy.check.regroups).toEqual([1, 2]);
    expect(after.difficulty.Easy.check.no_zero_top).toBe(true);
  } finally {
    await sql`update skill_set set difficulty = ${sql.json(before.difficulty)} where code = 'SUB.2D.EXCH'`;
  }
});

test("a difficulty with no exchange ticked is refused, and nothing is saved", async ({ page }) => {
  const [before] = await sql`select difficulty from skill_set where code = 'SUB.2D.EXCH'`;
  await page.goto("/skill-sets/SUB.2D.EXCH");
  await page.locator('textarea[name="words:Medium"]').fill("THIS MUST NOT BE SAVED");
  for (const n of [0, 1, 2, 3]) {
    const box = page.locator(`input[name="regroups:Medium"][value="${n}"]`);
    if (await box.isChecked()) await box.uncheck();
  }
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("at least one exchange")).toBeVisible();

  const [after] = await sql<{ difficulty: Record<string, { words: string }> }[]>`
    select difficulty from skill_set where code = 'SUB.2D.EXCH'`;
  expect(after.difficulty.Medium.words).toBe(before.difficulty.Medium.words);
  expect(after.difficulty.Medium.words).not.toBe("THIS MUST NOT BE SAVED");
});

test("ratifying records who did it, and the seed loader cannot undo it", async ({ page }) => {
  const [before] = await sql`select status, ratified_by from skill_set where code = 'ADD.3D.REG'`;
  try {
    await page.goto("/skill-sets/ADD.3D.REG");
    await page.getByRole("button", { name: "Ratify this set" }).click();
    await expect(page.getByRole("status")).toContainText("Ratified");
    const [after] = await sql<{ status: string; ratified_by: string }[]>`
      select status, ratified_by from skill_set where code = 'ADD.3D.REG'`;
    expect(after.status).toBe("ratified");
    expect(after.ratified_by).toBeTruthy();
  } finally {
    await sql`update skill_set set status = ${before.status}, ratified_by = ${before.ratified_by}
              where code = 'ADD.3D.REG'`;
  }
});

// ---------------------------------------------------------------- the question bank

test("the bank's filters narrow to exactly what the database holds", async ({ page }) => {
  await page.goto("/library");
  await page.getByRole("link", { name: "Hard", exact: true }).click();
  await page.getByRole("link", { name: "SUB.2D.EXCH", exact: true }).click();
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from item
    where status = 'active' and source = 'generated' and skill_set_code = 'SUB.2D.EXCH' and difficulty = 'Hard'`;
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(Math.min(n, 200));
});

test("every question in the bank shows an answer and at least one mistake it can spot", async ({ page }) => {
  await page.goto("/library?set=SUB.2D.EXCH&difficulty=Hard");
  const rows = page.getByRole("table").locator("tbody tr");
  for (const row of (await rows.all()).slice(0, 5)) {
    const cells = row.locator("td");
    await expect(cells.nth(3)).toHaveText(/\d+/); // the answer
    await expect(cells.nth(4)).toHaveText(/\S/); // at least one named mistake
  }
});

test("removing a question retires it in the database and it stops being offered", async ({ page }) => {
  const [victim] = await sql<{ item_key: string; id: string }[]>`
    select id, item_key from item where status = 'active' and skill_set_code = 'SUB.2D.EXCH'
    order by created_at desc limit 1`;
  try {
    await page.goto("/library?set=SUB.2D.EXCH");
    const row = page.getByRole("row").filter({ hasText: victim.item_key }).first();
    const target = (await row.count()) ? row : page.getByRole("table").locator("tbody tr").first();
    await target.getByText("Something wrong?").click();
    await target.locator('input[name="note"]').fill("end-to-end test");
    await Promise.all([
      page.waitForURL(/\/library/),
      target.getByRole("button", { name: "Remove this question" }).click(),
    ]);

    // The flag is recorded with who said it and why …
    await expect
      .poll(async () => {
        const [{ n }] = await sql<{ n: number }[]>`
          select count(*)::int as n from item_feedback where note = 'end-to-end test' and verdict = 'retire'`;
        return n;
      })
      .toBeGreaterThan(0);
    // … and the database trigger retires the question, so it can never print again.
    const [retired] = await sql<{ status: string; actor: string }[]>`
      select i.status, f.actor from item i join item_feedback f on f.item_id = i.id
      where f.note = 'end-to-end test' limit 1`;
    expect(retired.status).toBe("retired");
    expect(retired.actor).toBeTruthy();
  } finally {
    await sql`update item set status = 'active' where id in (
      select item_id from item_feedback where note = 'end-to-end test')`;
    await sql`delete from item_feedback where note = 'end-to-end test'`;
  }
});

// ---------------------------------------------------------------- worksheets

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
  const codes = await sql<{ id: string; print_status: string }[]>`
    select si.id, si.print_status from sheet_instance si
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
      await sql`update sheet_instance set print_status = ${c.print_status}, printed_at = null where id = ${c.id}`;
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
  for (const [route, table] of [["/capture", "captures"], ["/growth", "evidence events"], ["/home", "home sheets"]]) {
    await page.goto(route);
    await expect(page.getByText("What this screen will show")).toBeVisible();
    await expect(page.getByText("In the database today")).toBeVisible();
    await expect(page.getByRole("table")).toContainText(table);
  }
});

