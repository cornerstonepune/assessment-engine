/**
 * Step 11 — a child's next paper, chosen from their own ladder (goals/s11-focus-paper.yaml).
 *
 * How the areas are chosen and the questions drawn is the engine's own tests (tests/test_focus.py,
 * tests/test_focus_paper.py). This is what a teacher sees on the child's Growth page: which areas the next
 * paper works on and why, the questions, and a button that prints it.
 *
 * The child is the test's own, made once on the copy with checked answers and kept (evidence is
 * append-only, so a child with evidence is never deleted); the papers the test makes are removed.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "S11-TEST-C"; // answers on the taxonomy-shaped skills' rungs (ADR 0034)

async function testChild(): Promise<string> {
  const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (had) return had.id;
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const [{ id }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G3') returning id`;
  await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, 'Focus')`;
  // 3-digit − 3-digit: 2 of 8, taking the smaller digit from the larger four times; 2-digit + 2-digit 5 of 8, the
  // carry forgotten each time it was wrong; 2-digit + 1-digit 9 of 9. 3-digit − 3-digit is worked on at Easy (no
  // exchange, where that mistake cannot show); 2-digit + 2-digit at Medium, whose carries can show the forgotten one.
  const answers: [string, string, boolean, string[]][] = [
    ...Array(4).fill(["NUM.OPS.02", "R31", false, ["M_SMALL_FROM_LARGE"]]),
    ...Array(2).fill(["NUM.OPS.02", "R31", false, []]),
    ...Array(2).fill(["NUM.OPS.02", "R31", true, []]),
    ...Array(5).fill(["NUM.OPS.01", "R22", true, []]),
    ...Array(3).fill(["NUM.OPS.01", "R22", false, ["M_NOCARRY"]]),
    ...Array(9).fill(["NUM.OPS.01", "R21", true, []]),
  ];
  for (const [skill, rung, right, mistakes] of answers) {
    await sql`
      insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                  observed_at, confirmed_by)
      values (${tenant_id}, ${id}, ${skill}, ${rung}, ${right}, ${mistakes}, 'item', now(), 'e2e')`;
  }
  await sql`select rebuild_child_skill_state(${id}::uuid)`;
  return id;
}

async function clearUp(id: string) {
  await sql`delete from item_exposure where child_id = ${id}`;
  await sql`delete from sheet_instance where child_id = ${id} and kind = 'focus'`;
  await sql`delete from sheet_template where child_id = ${id} and source = 'focus'`;
}

let child = "";
test.beforeAll(async () => {
  child = await testChild();
  await clearUp(child);
});
test.afterAll(async () => {
  await clearUp(child);
  await sql.end();
});

test("a child's page says which areas the next paper works on and why, and makes it", async ({ page }) => {
  await page.goto(`/growth/${child}`);
  await expect(page.getByRole("heading", { name: "Next paper, proposed by the engine" })).toBeVisible();
  const areas = page.getByRole("list", { name: "Areas the next paper works on" });
  // the weakest first
  await expect(areas.getByRole("link", { name: "3-digit − 3-digit" })).toBeVisible();
  await expect(areas.getByText("Right 2 of 8 — the same mistake more than once")).toBeVisible();
  await expect(areas.getByRole("link", { name: "2-digit + 2-digit" })).toBeVisible();
  await expect(areas.getByText("can show the mistake").first()).toBeVisible();
  await expect(page.getByText("12 questions", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Approve this paper" }).click();
  await expect(page).toHaveURL(/\?paper=CS[0-9A-F]{6}$/);
  const qr = new URL(page.url()).searchParams.get("paper")!;
  await page.getByRole("region", { name: "Next paper, proposed by the engine" }).getByRole("link", { name: qr }).click();
  await expect(page.getByRole("heading", { name: `Paper ${qr}` })).toBeVisible();
  await expect(page.getByText("chosen from this child's own checked papers")).toBeVisible();
  const [made] = await sql<{ n: number }[]>`
    select coalesce(array_length(st.item_ids, 1), 0) as n from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id where si.qr_code = ${qr}`;
  expect(made.n).toBe(12);
});
