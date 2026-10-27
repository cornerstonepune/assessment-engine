/**
 * A paper reviewed before it prints: its questions, Remove, and Add from the bank (goals/paper_review_add_remove.yaml).
 * Nimish, 2026-10-27: "When a teacher generates an assessment, they should see a page where they can look at the actual
 * questions, and that should have an add/remove button".
 *
 * The rules (limits, what may change, the new code, the edit's row, a changed paper still read and marked) are the
 * engine's own tests (tests/test_edit_paper.py). This is what the educator sees and does.
 *
 * The child is the test's own, made once with checked answers and kept (evidence is append-only); its papers are removed.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "P5-REVIEW";
const REVIEW = /\/papers\/review\/(CS[0-9A-F]{6})$/;

async function testChild(): Promise<string> {
  const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (had) return had.id;
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const [{ id }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G3') returning id`;
  await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, 'Review')`;
  // 3-digit − 3-digit: 2 of 8, the smaller digit taken from the larger four times — the home paper's one area
  const answers: [string, string, boolean, string[]][] = [
    ...Array(4).fill(["NUM.OPS.02", "R31", false, ["M_SMALL_FROM_LARGE"]]),
    ...Array(2).fill(["NUM.OPS.02", "R31", false, []]),
    ...Array(2).fill(["NUM.OPS.02", "R31", true, []]),
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

const qrOf = (page: Page) => page.url().match(REVIEW)![1];
const status = (qr: string) =>
  sql<{ print_status: string; approved_by: string | null }[]>`select print_status, approved_by from sheet_instance where qr_code = ${qr}`.then((r) => r[0]);

/** Made from the child's page: it lands on its review page. */
async function made(page: Page): Promise<string> {
  await clearUp(child);
  await page.goto(`/growth/${child}`);
  await page.getByRole("button", { name: "Approve this home assessment" }).click();
  await expect(page).toHaveURL(REVIEW);
  return qrOf(page);
}

/** The paper's one area, as its first question's row names it. */
async function area(qr: string) {
  const [a] = await sql<{ skill: string; level: string; topic: string }[]>`
    select i.skill_set_code as skill, i.difficulty as level, s.topic_code as topic
    from sheet_instance si join sheet_template t on t.id = si.sheet_template_id
    join item i on i.id = t.item_ids[1] join skill s on s.code = i.skill_set_code where si.qr_code = ${qr}`;
  return a;
}

test("an educator makes a home assessment, removes a question, adds one through the dropdowns and approves it", async ({ page }) => {
  const first = await made(page);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Review this home assessment");
  const summary = page.locator("[data-summary]");
  await expect(summary).toContainText("12 questions");
  await expect(summary).toContainText("approved, not printed yet");
  const rows = page.getByRole("table", { name: "The paper's questions" }).locator("tbody tr");
  await expect(rows).toHaveCount(10); // ten a page (docs/ux-rules.md, rule 3); the rest on the next
  await expect(page.getByRole("navigation", { name: "The paper's questions pages" })).toBeVisible();

  // removing from an approved paper asks once, and says the approval is withdrawn
  await rows.first().getByRole("link", { name: "Remove" }).click();
  await expect(rows.first()).toContainText("Its approval is withdrawn");
  await rows.first().getByRole("button", { name: "Yes, remove it" }).click();
  await expect(page).toHaveURL(new RegExp(`/papers/review/(?!${first})CS[0-9A-F]{6}\\?`));
  await expect(page.getByRole("status").first()).toContainText("Removed: the paper now holds 11 questions.");
  await expect(page.getByRole("status").first()).toContainText("Its approval was withdrawn");
  await expect(summary).toContainText("11 questions");
  await expect(summary).toContainText("waiting for approval");
  const second = page.url().split("?")[0].match(REVIEW)![1];
  expect(await status(first)).toMatchObject({ print_status: "void" });
  expect(await status(second)).toEqual({ print_status: "new", approved_by: null });

  // add through the dropdowns: topic, then skill, then level, then the question, seen before it is added
  const a = await area(second);
  const bank = page.getByRole("region", { name: "Add a question from the bank" });
  // each choice reloads the page with the next dropdown narrowed to it
  await bank.getByLabel("Topic").selectOption(a.topic);
  await expect(page).toHaveURL(new RegExp(`topic=${a.topic}`));
  await bank.getByLabel("Skill").selectOption(a.skill);
  await expect(page).toHaveURL(new RegExp(`skill=${a.skill.replace(".", "\\.")}`));
  await bank.getByLabel("Level").selectOption(a.level);
  await expect(page).toHaveURL(new RegExp(`level=${a.level}`));
  const levels = await bank.getByLabel("Level").locator("option").allTextContents();
  expect(levels.slice(1).every((l) => ["Easy", "Medium", "Hard", "Advance"].includes(l))).toBe(true);
  const options = bank.locator(`select[name="q"]`).locator("option");
  await expect(options.nth(1)).toBeAttached();
  await bank.locator(`select[name="q"]`).selectOption({ index: 1 });
  await expect(page).toHaveURL(/[?&]q=/);
  const seeIt = page.getByRole("region", { name: "The chosen question" });
  await expect(seeIt).toBeVisible();
  await seeIt.getByRole("button", { name: "Add" }).click();
  await expect(page.getByRole("status").first()).toContainText("Added: the paper now holds 12 questions.");
  const third = page.url().split("?")[0].match(REVIEW)![1];
  const edits = await sql<{ qr_before: string; qr_after: string; changed_by: string }[]>`
    select qr_before, qr_after, changed_by from paper_edit where qr_before in (${first}, ${second}) order by created_at`;
  expect(edits).toEqual([
    { qr_before: first, qr_after: second, changed_by: TEST_STAFF.email },
    { qr_before: second, qr_after: third, changed_by: TEST_STAFF.email },
  ]);

  // approved here, in the educator's name, each paper on its own
  await page.getByRole("button", { name: "Approve this home assessment" }).click();
  await expect(page.getByRole("status").first()).toContainText("Approved in your name");
  expect(await status(third)).toEqual({ print_status: "printed", approved_by: TEST_STAFF.email });
});

test("an approved paper edited goes back to waiting, a printed one is read-only, a retired kind is not offered", async ({ page }) => {
  const qr = await made(page);
  const a = await area(qr);

  // a kind stopped at this level ("stop using this kind", #335) is not offered, nor are its questions
  const kinds = await sql<{ code: string; words: string }[]>`
    select distinct k.code, k.words from drawable_item d join question_type k on k.code = d.question_type
    where d.skill_set_code = ${a.skill} and d.difficulty = ${a.level} order by k.words`;
  expect(kinds.length).toBeGreaterThan(1);
  const stopped = kinds[0];
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const kindRow = (on: boolean) => sql`
    insert into skill_level_kind_stop (tenant_id, skill_code, difficulty, question_type, stopped, changed_by)
    values (${tenant_id}, ${a.skill}, ${a.level}, ${stopped.code}, ${on}, 'e2e')`;
  await kindRow(true);
  try {
    await page.goto(`/papers/review/${qr}?topic=${a.topic}&skill=${a.skill}&level=${a.level}`);
    const bank = page.getByRole("region", { name: "Add a question from the bank" });
    await expect(bank.locator(`select[name="q"]`)).toBeVisible();
    await expect(bank.locator("option", { hasText: stopped.words })).toHaveCount(0);
  } finally {
    await kindRow(false); // started again: a stop is never deleted, a restart is its own row
  }

  // printed: its print opened, it is shown read-only and says how to change it
  expect((await page.request.get(`/api/papers/print?qr=${qr}`)).ok()).toBe(true);
  await page.goto(`/papers/review/${qr}`);
  await expect(page.locator("[data-summary]")).toContainText("printed");
  await expect(page.getByText("This paper is already printed. Make a new one to change it.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Remove/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Remove" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Add a question from the bank" })).toHaveCount(0);
});
