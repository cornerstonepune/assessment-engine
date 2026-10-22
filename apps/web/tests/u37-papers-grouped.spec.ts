/**
 * U37 — Assessments grouped, and a class's papers to approve said child by child (goals/ux5-papers-grouped.yaml).
 * Nimish, 2026-10-11: "This cannot be just such a freaking long list of stuff. Need to make it more readable." and
 * "the assessment page needs to have the filter and the view by topic and all"; 2026-10-15: "All these things should be
 * expandable and collapsible. They should have the right set of columns which are important."
 *
 * A Grade 2 class of the test's own, its educator signed in for what only they see:
 * - this week, a class assessment on one skill: Asha's copy with the children, Bina's read with an answer waiting for
 *   a person, Chetan's to approve, and a spare to approve; Dev's plan could not be given a paper, and why is kept on it;
 *   Esha joined after the week was planned;
 * - a week long past, a class practice: Asha's copy with the children.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek, weekWords } from "../lib/week";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U37-CLASS";
const THIS = isoWeek();
const OLD = "2026-W30";
const QR = { asha: "CS370A01", bina: "CS370B02", chetan: "CS370C03", spare: "CS3705A1", old: "CS3700D1" };
const WHY = "has sat every worksheet at Hard (4)";
const EDUCATOR = { email: "u37-educator@cornerstone.test", name: "U37 Educator", role: "educator", classes: [SECTION] };
const PASSWORD = "u37-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let kids: Record<string, string> = {};
let skill = "";

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan", "Dev", "Esha"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  // one skill's worksheets from the library, at two levels
  const ws = await sql<{ id: string; item_ids: string[]; skill: string; level: string }[]>`
    select id, item_ids, skill_set_code as skill, difficulty as level from sheet_template
    where source = 'library' and retired_at is null and band = 'G2'
      and skill_set_code = (select skill_set_code from sheet_template where source = 'library' and retired_at is null
                            and band = 'G2' and difficulty = 'Hard' order by skill_set_code limit 1)
      and difficulty in ('Medium', 'Hard')
    order by difficulty = 'Hard' desc, code limit 4`;
  [{ name: skill }] = await sql<{ name: string }[]>`select name from skill where code = ${ws[0].skill}`;
  const paper = (qr: string, w: string, child: string | null, week: string, kind: string, status: string) => sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status,
                                approved_by, approved_at)
    select ${tenant}, ${qr}, ${w}, ${child}, ${week}, ${SECTION}, ${kind}, ${status},
           ${status === "new" ? null : "u37"}, ${status === "new" ? null : sql`now()`}
    where not exists (select 1 from sheet_instance where qr_code = ${qr})`;
  await paper(QR.asha, ws[0].id, kids.Asha, THIS, "assessment", "printed");
  await paper(QR.bina, ws[1].id, kids.Bina, THIS, "assessment", "printed");
  await paper(QR.chetan, ws[2].id, kids.Chetan, THIS, "assessment", "new");
  await paper(QR.spare, ws[3].id, null, THIS, "assessment", "new");
  await paper(QR.old, ws[1].id, kids.Asha, OLD, "practice", "printed");
  // Bina's copy read: one answer waits for a person
  await aReadPaper(sql, {
    qr: QR.bina,
    child: kids.Bina,
    template: ws[1].id,
    items: ws[1].item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  });
  // the week's plan: each child's level, and the paper they were handed; Dev's could not be, and why is kept;
  // Esha joined the class after it was made
  await sql`delete from prescription where child_id in ${sql(Object.values(kids))} and week = ${THIS}`;
  const sheet = async (qr: string) => (await sql<{ id: string }[]>`select id from sheet_instance where qr_code = ${qr}`)[0].id;
  for (const [who, level, qr] of [
    ["Asha", "Hard", QR.asha],
    ["Bina", "Hard", QR.bina],
    ["Chetan", "Medium", QR.chetan],
    ["Dev", "Hard", null],
  ] as const) {
    await sql`
      insert into prescription (tenant_id, child_id, week, kind, skill_set_code, difficulty, rule_fired, strand,
                                sheet_instance_id, no_paper, created_at)
      values (${tenant}, ${kids[who]}, ${THIS}, 'assessment', ${ws[0].skill}, ${level}, 'band_default', 'NUM',
              ${qr ? await sheet(qr) : null}, ${qr ? null : WHY}, now() - interval '1 day')`;
  }
  await sql`update child set created_at = now() where id = ${kids.Esha}`;
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

const week = (page: Page, w: string) => page.locator(`details[data-week="${w}"]`);

test("Assessments opens on its weeks, the newest open and the rest closed, each saying what waits in it", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/papers");
  // the educator's own class only: two weeks, the newest first
  await expect(page.locator("details[data-week]")).toHaveCount(2);
  expect(await page.locator("details[data-week]").evaluateAll((els) => els.map((e) => e.getAttribute("data-week")))).toEqual([THIS, OLD]);
  await expect(week(page, THIS)).toHaveAttribute("open", "");
  await expect(week(page, OLD)).not.toHaveAttribute("open", "");
  // each week one line: its name, how many assessments, and only what waits
  const line = week(page, THIS).locator("> summary");
  await expect(line).toContainText(weekWords(THIS));
  await expect(line).toContainText(/1 assessment\b.*1 to approve\b.*1 to check\b/);
  await expect(week(page, OLD).locator("> summary")).toContainText(/1 assessment\b.*nothing waiting/);
  // one line an assessment: what it is, its class and where its copies stand; no copies until it is opened
  const a = week(page, THIS).locator("[data-assessment]");
  await expect(a).toHaveCount(1);
  await expect(a).toContainText(skill);
  await expect(a).toContainText(`Grade 2 · ${SECTION}`);
  await expect(page.getByRole("table", { name: /: each copy$/ })).toHaveCount(0);
  await page.context().close();
});

test("an assessment opens in place to its copies in roll order, its spares on one line", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/papers");
  await week(page, THIS).locator("[data-assessment]").getByRole("link", { name: skill }).click();
  await expect(page).toHaveURL(/[?&]open=/);
  const copies = week(page, THIS).getByRole("table", { name: `${skill}: each copy` });
  await expect(copies).toBeVisible();
  await expect(copies.locator("thead th")).toHaveText(["Roll", "Child", "Level", "Stage", "Waiting", "Score"]);
  const rows = copies.locator("tbody tr");
  await expect(rows).toHaveCount(3);
  expect(await rows.evaluateAll((trs) => trs.map((t) => t.querySelectorAll("td")[1].textContent?.trim()))).toEqual(["Asha", "Bina", "Chetan"]);
  const cells = (i: number) => rows.nth(i).locator("td");
  await expect(cells(0).nth(2)).toHaveText("Hard");
  await expect(cells(1).nth(3)).toHaveText("to check");
  await expect(cells(1).nth(4)).toHaveText("1");
  await expect(cells(2).nth(3)).toHaveText("to approve");
  // a copy opens where its work is: one not read yet, its page; one read, its answers
  await expect(cells(0).getByRole("link", { name: "Asha" })).toHaveAttribute("href", `/worksheets/${QR.asha}`);
  await expect(cells(1).getByRole("link", { name: "Bina" })).toHaveAttribute("href", /^\/capture\/[0-9a-f-]{36}$/);
  // the spares: one line under the copies
  const spares = week(page, THIS).locator("[data-spares]");
  await expect(spares).toHaveText(/^1 spare copy, with the pack:\s*CS3705A1$/);
  await page.context().close();
});

test("the topic and stage rows stay, the other filters fold, and a filter opens every week it leaves", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/papers");
  await expect(page.locator("details[data-week]").first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Topic" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Papers by stage" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "View" })).toHaveCount(0);
  const more = page.locator("details[data-filters]");
  await expect(more).not.toHaveAttribute("open", "");
  // a child chosen: their papers, every week open, each assessment showing their copy
  await page.goto(`/papers?child=${kids.Asha}`);
  await expect(more).toHaveAttribute("open", "");
  await expect(week(page, THIS)).toHaveAttribute("open", "");
  await expect(week(page, OLD)).toHaveAttribute("open", "");
  await expect(week(page, OLD).getByRole("link", { name: "Asha" })).toHaveAttribute("href", `/worksheets/${QR.old}`);
  await expect(week(page, THIS).getByRole("link", { name: "Bina" })).toHaveCount(0);
  await page.context().close();
});

test("class papers to approve names each child, says why a child has no paper, and counts what it approves", async ({ page }) => {
  await page.goto(`/papers/approve?section=${SECTION}&week=${THIS}&kind=assessment`);
  const table = page.getByRole("table", { name: "Each child's paper this week" });
  await expect(table.locator("thead th")).toHaveText(["Roll", "Child", "Level", "Paper", ""]);
  expect(await table.locator("tbody tr").evaluateAll((trs) => trs.map((t) => t.querySelectorAll("td")[1].textContent?.trim()))).toEqual([
    "Asha",
    "Bina",
    "Chetan",
  ]);
  // the level, and why it was chosen, in one cell
  await expect(table.locator("tbody tr").nth(2).locator("td").nth(2)).toContainText("Medium");
  // every child of the class without a paper, by name, and why
  const none = page.getByRole("region", { name: "No paper this week" });
  await expect(none.getByRole("listitem")).toHaveCount(2);
  await expect(none.getByRole("listitem").filter({ hasText: "Dev" })).toContainText(WHY);
  await expect(none.getByRole("listitem").filter({ hasText: "Esha" })).toContainText("joined the class after this week was planned");
  // the button says what one tap approves: Chetan's paper and the spare
  await expect(page.getByRole("button", { name: "Approve 1 paper and 1 spare" })).toBeEnabled();
});
