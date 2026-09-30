/**
 * S26 — the right answer, shown as the engine stores it and corrected by an educator for every child
 * (goals/s26-the-right-answer-shown-and-corrected.yaml).
 *
 * Nimish, 2026-09-30: "in any correction, the system should show what the right answer is as stored in the system"
 * and "the key can be changed by an educator, not an issue". The paper is entered by the engine as a real paper is.
 * One child's copy is read:
 * - 4a, "48 + 35 =", left blank;
 * - 4b, the number line's first box, read 78, against a key typed 80 in the file.
 */
import { expect, type Page, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
// Each run gets its own paper. A changed right answer is a row nobody deletes (append-only), so after a run changes
// a paper's key, the key stays changed.
const CODE = `S26-${Date.now().toString(36).toUpperCase()}`;
const CHANGE = "Is the right answer wrong? Change it for every child";
let paper = "";

test.beforeAll(async () => {
  const dir = mkdtempSync(path.join(tmpdir(), "s26-"));
  const file = path.join(dir, `${CODE}.json`);
  writeFileSync(
    file,
    JSON.stringify({
      code: CODE,
      title: "S26 paper",
      band: "G4",
      week: CODE,
      date: "2026-09-03",
      pages: [{ n: 1, mask: 0 }],
      items: [
        { n: 4, part: "a", page: 1, expr: "48 + 35", question: "48 + 35 =" },
        { n: 4, part: "b", page: 1, kind: "missing", rung: "R7", answer: 80, question: "the number line, first box" },
      ],
    }),
  );
  execFileSync(path.resolve(__dirname, "../../../bin/engine"), ["legacy", "paper", file], { env: { ...process.env } });
  rmSync(dir, { recursive: true });
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const [{ id: child }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${CODE}, 'G4') returning id`;
  await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${child}, 'Rudra')`;
  const [t] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where source = 'legacy' and batch_id = ${CODE}`;
  const [{ id: sheet }] = await sql<{ id: string }[]>`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
    values (${tenant_id}, ${CODE}, ${t.id}, ${child}, 'returned') returning id`;
  const [{ id: cap }] = await sql<{ id: string }[]>`
    insert into capture (tenant_id, path, pages, status, sheet_instance_id)
    values (${tenant_id}, ${CODE + ".pdf"}, 1, 'processed', ${sheet}) returning id`;
  // 4a: blank, waiting for a person. 4b: 78, as a person typed it, wrong against the file's 80.
  const answers = [
    { i: 0, status: "needs_teacher", read: "", typed: false },
    { i: 1, status: "wrong", read: "78", typed: true },
  ];
  for (const a of answers) {
    const raw = JSON.stringify({ child_answer: a.read, answer_state: a.read ? "written" : "blank", why: a.read ? "" : "no number" });
    const [{ id }] = await sql<{ id: string }[]>`
      insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status)
      values (${tenant_id}, ${cap}, ${t.item_ids[a.i]}, 'a', ${raw}, ${a.status}) returning id`;
    if (a.typed)
      await sql`
        insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by)
        values (${tenant_id}, ${child}, ${cap}, ${id}, ${a.read}, ${a.read}, 'e2e')`;
  }
  paper = sheet;
});
test.afterAll(async () => sql.end());

// One answer's card, by its question; the answers the engine marked itself sit folded, so the fold is opened first.
async function card(page: Page, slot: string) {
  const fold = page.getByText(/the engine marked itself — open to check/);
  if (await fold.count()) await fold.first().click();
  return page.locator("li", { has: page.getByText(`Question ${slot}`, { exact: true }) });
}

test("every answer shows its right answer as the engine stores it", async ({ page }) => {
  await page.goto(`/capture/${paper}`);
  await expect(await card(page, "4a")).toContainText("Right answer 83");
  await expect(await card(page, "4b")).toContainText("Right answer 80");
});

test("an educator changes a right answer for every child, and code refuses one the sum contradicts", async ({ page }) => {
  await page.goto(`/capture/${paper}`);
  const a = await card(page, "4a");
  await a.getByText(CHANGE).click();
  await a.getByLabel("The right answer is").fill("78");
  await a.getByRole("button", { name: "Change it for every child" }).click();
  await expect(page.getByText("Nothing was changed: 48 + 35 is 83, so 78 cannot be its right answer")).toBeVisible();

  const b = await card(page, "4b");
  await b.getByText(CHANGE).click();
  await b.getByLabel("The right answer is").fill("78");
  await b.getByRole("button", { name: "Change it for every child" }).click();
  await expect(page.getByText(/The right answer to question 4b is now 78, for every child\. 1 answer was marked again/)).toBeVisible();
  await expect(await card(page, "4b")).toContainText("Right answer 78 · changed from 80 by e2e@cornerstone.test");
  const [{ status }] = await sql<{ status: string }[]>`
    select r.status from item_result r join item i on i.id = r.item_id where i.item_key = ${`legacy/${CODE}/4b`}`;
  expect(status).toBe("correct");
});
