/**
 * Step 8, widened — the team's addition & subtraction taxonomy (goals/s8t-taxonomy-coverage.yaml).
 *
 * The rules are the engine's own tests (tests/test_taxonomy.py, tests/test_new_kinds.py). This is what a
 * teacher sees on the copy: every kind of question the bank did not have is on the Question bank, drawn
 * as the child meets it (boxes, a missing sign, a fact family, a check) and never as a code; a worksheet
 * of a new skill opens with its twelve questions and prints; a Grade 1 worksheet has sums in columns.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

// the kind as a teacher reads it (components/question.tsx), and words the child's question itself carries
const NEW_KINDS: [string, string, RegExp][] = [
  ["missing_digit", "missing digit", /□|The letter A|How many different digits/],
  ["equation", "make both sides equal", /□|true or false|<, = or >/i],
  ["fact_family", "fact family", /Use it to finish these facts/],
  ["inverse_check", "check with the inverse", /^Check .* with (a subtraction|an addition)/m],
  ["choose_estimate", "closest estimate", /Which is closest to/],
  ["possible_answer", "could it be right?", /could that be right\?/],
  ["odd_even", "odd or even", /be odd or even\?/],
  ["break_apart", "tens, then ones", /the tens first, then the ones/],
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test("every new kind of question is on the Question bank, drawn as the child meets it", async ({ page }) => {
  for (const [fmt, label, words] of NEW_KINDS) {
    const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from item where status = 'active' and fmt = ${fmt}`;
    expect(n, `${fmt} questions in the bank`).toBeGreaterThan(0);
    await page.goto(`/library?fmt=${fmt}#questions`);
    const main = page.getByRole("main");
    await expect(main.getByText(label, { exact: true }).first()).toBeVisible();
    const text = await main.getByRole("table").last().innerText();
    expect(text, fmt).toMatch(words);
    expect(text, `${fmt}: a code on the page`).not.toMatch(CODE);
  }
});

test("a worksheet of each new skill opens with its twelve questions and prints", async ({ page }) => {
  for (const skill of ["MISSING.DIGIT", "EQUALITY.INVERSE", "ADD.MANY", "ESTIMATE.HUNDRED"]) {
    const [ws] = await sql<{ code: string }[]>`
      select code from sheet_template where source = 'library' and retired_at is null and skill_set_code = ${skill}
      order by difficulty, variant limit 1`;
    expect(ws, `${skill} has worksheets`).toBeTruthy();
    await page.goto(`/worksheets/${ws.code}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Worksheet ${ws.code}`);
    await expect(page.getByRole("table", { name: "Questions and answers" }).locator("tbody tr")).toHaveCount(12);
    const pdf = await page.request.get(`/api/worksheet/${ws.code}`);
    expect(pdf.status(), ws.code).toBe(200);
    expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");
  }
});

test("a story whose numbers sit in a table shows the table on screen", async ({ page }) => {
  const [q] = await sql<{ code: string; stem: string; label: string; n: string }[]>`
    select t.code, i.stem, i.spec -> 'table' -> 0 ->> 0 as label, i.spec -> 'table' -> 0 ->> 1 as n
    from sheet_template t join item i on i.id = any(t.item_ids)
    where t.source = 'library' and t.retired_at is null and i.spec ? 'table' order by t.code limit 1`;
  expect(q, "a worksheet holds a table story").toBeTruthy();
  await page.goto(`/worksheets/${q.code}`);
  // a worksheet can hold several stories of the same wording with different numbers: find this one by its number
  const row = page
    .getByRole("table", { name: "Questions and answers" })
    .locator("tbody tr")
    .filter({ hasText: q.stem })
    .filter({ hasText: q.n })
    .first();
  await expect(row).toContainText(q.label);
});

test("a Grade 1 worksheet has sums in columns as well as in a line", async () => {
  const rows = await sql<{ code: string; columns: number; lines: number }[]>`
    select t.code,
           count(*) filter (where i.fmt = 'column_grid')::int as columns,
           count(*) filter (where i.fmt = 'bare_sum')::int as lines
    from sheet_template t join item i on i.id = any(t.item_ids)
    where t.source = 'library' and t.retired_at is null and t.skill_set_code = 'ADD.1D1D' and t.difficulty = 'Medium'
    group by t.code`;
  expect(rows.length).toBeGreaterThanOrEqual(10);
  for (const r of rows) {
    expect(r.columns, `${r.code} sums in columns`).toBeGreaterThan(0);
    expect(r.lines, `${r.code} sums in a line`).toBeGreaterThan(0);
  }
});
