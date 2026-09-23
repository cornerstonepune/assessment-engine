/**
 * Step 7 — a child's paper is a worksheet from the library (goals/s7-paper-from-library.yaml).
 *
 * The hand-out's rules are the engine's own tests (tests/test_paper_from_library.py). This is what a
 * teacher sees, on the copy, for a week the engine builds the way the n8n flow asks it to: the week's
 * list names each child's worksheet, a paper says which worksheet it is and opens that worksheet's own
 * page, and a spare is listed with the week it was printed for.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
// A real class on the copy and a week of the test's own: its rows are removed afterwards, the class is
// never touched (a child cannot be deleted — evidence is append-only, and the guard sees a cascade).
const SECTION = "G2";
const WEEK = "S7-TEST";
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
  await clearUp();
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from child where section = ${SECTION} and active`;
  await engine("/week/prescribe", { section: SECTION, week: WEEK, skill_set: "SUB.2D2D" });
  const built = await engine("/week/assemble", { section: SECTION, week: WEEK });
  expect(built.short, "every child in the class is given a worksheet").toEqual([]);
  expect(built.sheets).toBe(n);
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
