/**
 * U64 — An educator stops a kind of question at a level, and uses it again (goals/gen_retire_a_kind.yaml). Nimish,
 * 2026-10-26: "the educator also, today, does not want certain types of questions. They should be able to delete those
 * kinds of questions from the bank itself."
 *
 * At 1440 px, on a Maths skill approved at every level whose level draws two kinds or more: the educator presses "Stop
 * using this kind of question", reads how many questions and past papers it touches before anything changes, confirms;
 * the level says the kind is stopped and waits for approval, no new paper may draw it there, and it is used again with
 * one press. A stop and a restart are rows never deleted, so a run leaves the kind in use; approvals are put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

type Kind = { code: string; level: string; kind: string; words: string; n: number };
let k: Kind;
let kept: unknown;
// the papers other specs approved this week that the stop sends back for approval, as they were: put back after
let papers: { qr_code: string; print_status: string; printed_at: Date | null; approved_by: string | null; approved_at: Date | null }[] = [];

const drawable = async () =>
  (await sql<{ n: number }[]>`select count(*)::int as n from drawable_item
    where skill_set_code = ${k.code} and difficulty = ${k.level} and question_type = ${k.kind}`)[0].n;

test.beforeAll(async () => {
  [k] = await sql<Kind[]>`
    with k as (select skill_set_code as code, difficulty as level, question_type as kind, count(*)::int as n
               from drawable_item group by 1, 2, 3),
         many as (select code, level from k group by 1, 2 having count(*) > 1)
    select k.code, k.level, k.kind, q.words, k.n from k join many using (code, level)
    join question_type q on q.code = k.kind join difficulty d on d.code = k.level
    order by k.code, d.ord, k.kind limit 1`; // the first level, so its row is on the table's first page
  [{ kept }] = await sql<{ kept: unknown }[]>`select level_approved as kept from skill where code = ${k.code}`;
  await sql`update skill set level_approved = (select jsonb_object_agg(x, jsonb_build_object('by', 'Achal', 'at', now()))
                                               from jsonb_object_keys(difficulty) x) where code = ${k.code}`;
});

test.afterAll(async () => {
  await sql`update skill set level_approved = ${sql.json(kept as never)} where code = ${k.code}`;
  for (const p of papers)
    await sql`update sheet_instance set print_status = ${p.print_status}, printed_at = ${p.printed_at}, approved_by = ${p.approved_by},
                approved_at = ${p.approved_at} where qr_code = ${p.qr_code}`;
  await sql.end();
});

test("an educator stops a kind at a level, is told what it touches first, and switches it back on", async ({ page }) => {
  await page.goto(`/skill-sets/${k.code}`);
  const row = page.locator(`tr[data-kind="${k.kind}"][data-level="${k.level}"]`);
  await expect(row).toContainText("in use");
  await row.getByRole("link", { name: `Stop using “${k.words}” at ${k.level}` }).click();

  // what it touches, said before anything changes
  const confirm = page.locator(`[data-confirm-stop="${k.kind}"]`);
  await expect(confirm).toContainText(`Stop using “${k.words}” at ${k.level}?`);
  await expect(confirm).toContainText(`${k.n} question${k.n === 1 ? "" : "s"} in the bank will not be drawn for any new paper`);
  await expect(confirm).toContainText(/past papers? holds?/);
  await expect(confirm).toContainText("Nothing is deleted");
  await expect(confirm).toContainText(`Until ${k.level} is approved again, no new paper is drawn from it`);
  expect(await drawable()).toBe(k.n);
  const listed = confirm.locator("[data-withdraw]");
  const withdraw = (await listed.count()) ? ((await listed.getAttribute("data-withdraw")) ?? "").split(" ").filter(Boolean) : [];
  if (withdraw.length)
    papers = await sql`select qr_code, print_status, printed_at, approved_by, approved_at from sheet_instance where qr_code = any(${withdraw})`;

  await confirm.getByRole("button", { name: "Stop using this kind of question" }).click();
  await expect(page.getByText("The kind is stopped: no new paper draws it")).toBeVisible();
  await expect(page.getByText(`${k.level} waits for approval again`)).toBeVisible();
  await expect(row).toContainText("stopped");
  expect(await drawable()).toBe(0);
  const [{ approved }] = await sql<{ approved: boolean }[]>`select level_approved ? ${k.level} as approved from skill where code = ${k.code}`;
  expect(approved).toBe(false);

  await row.getByRole("button", { name: `Use “${k.words}” again at ${k.level}` }).click();
  await expect(page.getByText("The kind is in use again.")).toBeVisible();
  await expect(row).toContainText("in use");
  // the level waits for approval; approved again, it draws the kind as before
  await sql`update skill set level_approved = level_approved || jsonb_build_object(${k.level}::text,
              jsonb_build_object('by', 'Achal', 'at', now())) where code = ${k.code}`;
  expect(await drawable()).toBe(k.n);
});
