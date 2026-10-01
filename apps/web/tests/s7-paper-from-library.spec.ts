/**
 * Step 7 — a child's paper is a worksheet from the library (goals/s7-paper-from-library.yaml).
 *
 * The hand-out's rules are the engine's own tests (tests/test_paper_from_library.py). This is what a
 * teacher sees, on the copy, for a week the engine builds the way the n8n flow asks it to: the week's
 * list names each child's worksheet, a paper says which worksheet it is and opens that worksheet's own
 * page, and a spare is listed with the week it was printed for. And the week's own screen: every child with a level and
 * a reason, a level changed with its reason, the pack approved, spares with no name (from e2e.spec.ts).
 *
 * The class is the test's own (tests/rows.ts), four Grade 2 children made once and kept. It was live's "G2" until
 * 2026-10-01, and the week tests read live's "G3" week T2W1, so on any other database they failed or skipped
 * themselves (goals/p1-browser-tests-in-ci.yaml).
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
// A class and a week of the test's own: the week's rows are removed afterwards; the class is kept.
const SECTION = "S7-TEST";
const WEEK = "S7-WEEK";
const LIST = `/worksheets?section=${SECTION}&week=${WEEK}&kind=practice`;

async function engine(path: string, body: object) {
  const r = await fetch(`http://127.0.0.1:${ENGINE_PORT}${path}`, {
    method: "POST",
    headers: {
      "X-Engine-Key": process.env.E2E_ENGINE_KEY!,
      "content-type": "application/json",
      // a fresh key each run, so a stored result from an earlier run is never replayed
      "Idempotency-Key": `s7-${path}-${Date.now()}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json();
}

async function clearUp() {
  await sql`delete from item_exposure where week = ${WEEK}`;
  await sql`delete from prescription where week = ${WEEK}`;
  await sql`delete from sheet_instance where week = ${WEEK}`;
}

const papers = () =>
  sql<{ qr_code: string; worksheet: string }[]>`
    select si.qr_code, st.code as worksheet from sheet_instance si join sheet_template st on st.id = si.sheet_template_id
    where si.section = ${SECTION} and si.week = ${WEEK} and si.child_id is not null order by si.qr_code`;

test.beforeAll(async () => {
  await aClass(sql, SECTION, "G2", ["Anya", "Bilal", "Chitra", "Dhruv"]);
  await clearUp();
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from child where section = ${SECTION} and active`;
  await engine("/week/prescribe", { section: SECTION, week: WEEK, skill_set: "SUB.2D2D" });
  const built = await engine("/week/assemble", { section: SECTION, week: WEEK });
  expect(built.short, "every child in the class is given a worksheet").toEqual([]);
  expect(built.sheets).toBe(n);
  // printed as the n8n flow prints it, so each paper's page is the PDF the engine rendered
  await engine("/week/render", { section: SECTION, week: WEEK, actor: "e2e" });
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

test("the week's list names the worksheet each child was given", async ({ page }) => {
  const rows = await papers();
  expect(rows.length).toBeGreaterThan(1);
  expect(new Set(rows.map((r) => r.worksheet)).size, "no two children share a worksheet").toBe(rows.length);
  await page.goto(LIST);
  for (const r of rows) {
    expect(r.worksheet).toMatch(/^R\d+-[EMHA]\d{2}$/);
    await expect(page.getByRole("link", { name: r.worksheet, exact: true })).toBeVisible();
  }
});

test("a paper says which worksheet it is, and that worksheet's own page opens from it", async ({ page }) => {
  const [r] = await papers();
  await page.goto(`/worksheets/${r.qr_code}`);
  await expect(page.getByText("from the library, one of")).toBeVisible();
  await page.getByRole("link", { name: r.worksheet, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/worksheets/${r.worksheet}$`));
  await expect(page.getByRole("heading", { name: `Worksheet ${r.worksheet}` })).toBeVisible();
});

test("a spare is listed with the week it was printed for", async ({ page }) => {
  const spares = await sql<{ qr_code: string }[]>`
    select qr_code from sheet_instance where section = ${SECTION} and week = ${WEEK} and child_id is null`;
  expect(spares.length).toBeGreaterThan(0);
  await page.goto(LIST);
  for (const s of spares) await expect(page.getByRole("link", { name: new RegExp(s.qr_code) })).toBeVisible();
});

test("a paper opens from its code: the page as printed, how it was drawn, and its whole key", async ({ page }) => {
  const [paper] = await sql<
    { qr: string; section: string; week: string; kind: string; n: number; pool: number; source: string; code: string }[]
  >`
    select si.qr_code as qr, c.section, p.week, p.kind, array_length(st.item_ids, 1) as n, st.source, st.code,
           (select count(*)::int from item i where i.status = 'active' and i.source = 'generated'
              and i.skill_set_code = st.skill_set_code and i.difficulty = st.difficulty) as pool
    from prescription p
    join child c on c.id = p.child_id
    join sheet_instance si on si.id = p.sheet_instance_id
    join sheet_template st on st.id = si.sheet_template_id
    where si.pdf_path is not null and c.section = ${SECTION} and p.week = ${WEEK}
    order by si.created_at limit 1`;
  expect(paper, "a paper of the week, rendered").toBeTruthy();

  await page.goto(`/worksheets?section=${paper.section}&week=${paper.week}&kind=${paper.kind}`);
  await page.getByRole("link", { name: paper.qr, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Paper ${paper.qr}`);
  await expect(page.getByRole("table", { name: "Answer key" }).locator("tbody tr")).toHaveCount(paper.n);
  // a library worksheet says which one it is; a paper generated before the library, the pool it was drawn from
  await expect(
    page.getByText(
      paper.source === "library"
        ? `Worksheet ${paper.code} from the library, one of`
        : `${paper.n} picked at random from ${paper.pool.toLocaleString("en-IN")}`,
    ),
  ).toBeVisible();

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
    where c.section = ${SECTION} and p.week = ${WEEK} and p.kind = 'practice'`;
  await page.goto(LIST);
  const rows = page.getByRole("table", { name: "Each child's paper this week" }).locator("tbody tr");
  await expect(rows).toHaveCount(n);
  for (const row of await rows.all()) {
    await expect(row).toContainText(/Easy|Medium|Hard|Advance/);
    await expect(row).toContainText(/level|showed|hand/); // every row explains itself
  }
});

test("every child's paper has its own code, and no two children share questions", async ({ page }) => {
  await page.goto(LIST);
  // The page streams in behind its loading screen: wait for the table before reading its cells.
  const week = page.getByRole("table", { name: "Each child's paper this week" });
  await expect(week.locator("tbody tr").first()).toBeVisible();
  const codes = await week.locator("tbody tr td:nth-child(4)").allInnerTexts();
  // a cell reads "CS1A2B3C · R22-H03": the paper's own code, then the library worksheet it is
  const real = codes.map((c) => c.match(/\bCS[0-9A-F]{6}\b/)?.[0]).filter((c): c is string => !!c);
  expect(real.length).toBeGreaterThan(0);
  expect(new Set(real).size).toBe(real.length);

  const [{ shared }] = await sql<{ shared: number }[]>`
    select count(*)::int as shared from sheet_template a join sheet_template b
    on a.id < b.id and a.item_ids && b.item_ids
    where a.week = ${WEEK} and b.week = ${WEEK} and a.child_id is not null and b.child_id is not null`;
  expect(shared).toBe(0);
});

test("changing one child's level writes the reason and survives the next prescribe", async ({ page }) => {
  const [before] = await sql<{ id: string; difficulty: string; rule_fired: string }[]>`
    select p.id, p.difficulty, p.rule_fired from prescription p join child c on c.id = p.child_id
    where c.section = ${SECTION} and p.week = ${WEEK} and c.roll_no = '1'`;
  try {
    await page.goto(LIST);
    const row = page.getByRole("table", { name: "Each child's paper this week" }).locator("tbody tr").first();
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
    await expect(page.getByRole("table", { name: "Each child's paper this week" })).toContainText("she was away all week");
  } finally {
    await sql`update prescription set difficulty = ${before.difficulty}, rule_fired = ${before.rule_fired},
              override_by = null, override_reason = null where id = ${before.id}`;
  }
});

test("a level change with no reason is refused and nothing moves", async ({ page }) => {
  const [before] = await sql<{ id: string; difficulty: string }[]>`
    select p.id, p.difficulty from prescription p join child c on c.id = p.child_id
    where c.section = ${SECTION} and p.week = ${WEEK} and c.roll_no = '2'`;
  await page.goto(LIST);
  const row = page.getByRole("table", { name: "Each child's paper this week" }).locator("tbody tr").nth(1);
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
    select id, print_status, approved_by, approved_at from sheet_instance
    where section = ${SECTION} and week = ${WEEK} and kind = 'practice'`;
  try {
    await page.goto(LIST);
    await page.getByRole("button", { name: "Approve and print" }).click();
    await expect(page.getByRole("status")).toContainText("Approved");

    const [{ n }] = await sql<{ n: number }[]>`
      select count(*)::int as n from sheet_instance
      where section = ${SECTION} and week = ${WEEK} and kind = 'practice' and print_status = 'printed'`;
    expect(n).toBeGreaterThan(0);
    await expect(page.getByRole("table", { name: "Each child's paper this week" })).toContainText("printed");
  } finally {
    for (const c of codes) {
      await sql`update sheet_instance set print_status = ${c.print_status}, printed_at = null,
                approved_by = ${c.approved_by}, approved_at = ${c.approved_at} where id = ${c.id}`;
    }
  }
});

test("spare copies are listed and carry no child's name", async ({ page }) => {
  await page.goto(LIST);
  const panel = page.locator("section").filter({ hasText: "Spare copies" });
  await expect(panel).toContainText(/CS[0-9A-F]{6}/);
  // every copy listed as a spare is one made for no child
  const shown = (await panel.innerText()).match(/\bCS[0-9A-F]{6}\b/g) ?? [];
  const [{ named }] = await sql<{ named: number }[]>`
    select count(*)::int as named from sheet_instance where qr_code = any(${shown}) and child_id is not null`;
  expect(named).toBe(0);
});
