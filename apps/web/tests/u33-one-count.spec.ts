/**
 * U33 — one count for one thing (goals/ux2-one-count-one-thing.yaml). Nimish, 2026-10-15: "You really need to run a
 * thorough UI/UX skill here." The audit found the same number said three ways: "Grade 1 · G2-C" on a Grade 2 class's
 * papers, 12 class papers to approve on Today and 18 on Assessments, the bank 21,250, 28,705 and 28,717 on three pages,
 * the worksheet library 1,872 above its list and 2,738 in its pager.
 *
 * A Grade 2 class of the test's own (tests/rows.ts) is given a Grade 1 worksheet as class practice: a copy for each of
 * its two children and one spare, as the engine prints a pack. Its papers and their week are taken away after.
 */
import { randomBytes } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U33-CLASS";
const WEEK = "2026-W50";
let kids: Record<string, string> = {};

const qr = () => `CS${randomBytes(3).toString("hex").toUpperCase()}`;
const number = (s: string) => Number(s.replace(/[^\d]/g, "")) || 0;

async function clearUp() {
  await sql`delete from prescription where week = ${WEEK} and child_id in (select id from child where section = ${CLASS})`;
  await sql`delete from sheet_instance where section = ${CLASS} and week = ${WEEK}`;
}

test.beforeAll(async () => {
  kids = await aClass(sql, CLASS, "G2", ["Asha", "Bilal"]);
  await clearUp();
  // a Grade 1 worksheet from the library, given to the Grade 2 class: its own grade is not the class's
  const [w] = await sql<{ id: string; tenant_id: string; skill_set_code: string; difficulty: string }[]>`
    select id, tenant_id, skill_set_code, difficulty from sheet_template
    where source = 'library' and retired_at is null and band = 'G1' order by code limit 1`;
  for (const id of Object.values(kids)) {
    const [{ id: copy }] = await sql<{ id: string }[]>`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status, section, week, kind)
      values (${w.tenant_id}, ${qr()}, ${w.id}, ${id}, 'new', ${CLASS}, ${WEEK}, 'practice') returning id`;
    await sql`
      insert into prescription (tenant_id, child_id, week, rule_fired, skill_set_code, difficulty, kind, sheet_instance_id)
      values (${w.tenant_id}, ${id}, ${WEEK}, 'band_default', ${w.skill_set_code}, ${w.difficulty}, 'practice', ${copy})`;
  }
  // the spare: the same worksheet, the class's, no child's
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status, section, week, kind)
    values (${w.tenant_id}, ${qr()}, ${w.id}, null, 'new', ${CLASS}, ${WEEK}, 'practice')`;
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

const ours = (page: Page) => page.getByRole("table").locator("tbody tr").filter({ hasText: CLASS });

test("a class paper carries its class's grade, a spare copy too", async ({ page }) => {
  const [{ band }] = await sql<{ band: string }[]>`select class_band(tenant_id, ${CLASS}) as band from child where section = ${CLASS} limit 1`;
  expect(band, "the class's grade, the database's one rule").toBe("G2");
  await page.goto(`/papers?class=${CLASS}`);
  await expect(ours(page)).toHaveCount(1);
  await expect(ours(page)).toContainText(`Grade 2 · ${CLASS}`);
  // the class's one assessment, opened by itself: its two children's copies, and the spare with them, the class's too
  // (goals/ux5-papers-grouped.yaml)
  await expect(page.getByRole("table", { name: /: each copy$/ }).locator("tbody tr")).toHaveCount(2);
  await expect(page.locator("[data-spares]"), "a spare copy is the class's too").toContainText("1 spare copy, with the pack");
});

test("the class papers Today counts are the copies the pages it opens show waiting", async ({ page }) => {
  await page.goto(`/today?kind=classpaper&class=${CLASS}`);
  const item = page.locator("tr[data-kind=classpaper]").filter({ hasText: `${CLASS} · class practice` });
  await expect(item).toContainText("2 papers");

  // Assessments: the two children's copies wait to be approved; the spare rides with them, counted apart
  await page.goto(`/papers?class=${CLASS}`);
  // made, none yet printed: the next thing is to print them (a class's papers are approved as they are printed)
  await expect(ours(page).locator("[data-action=print]")).toHaveText("Print");
  await expect(ours(page).locator('[data-status="next"]')).toHaveCount(1);
  const status = page.locator('[data-filterbar] select[name="status"] option[value="print"]');
  await expect(status, "the class's assessment waiting to be printed").toHaveText(/^To print \(1\)$/);

  // the approve page Today's line opens: two copies to approve, the spare among the spare copies, the button counting
  // them as Today does (goals/ux5-papers-grouped.yaml)
  await page.goto(`/today?kind=classpaper&class=${CLASS}`);
  await page.locator("tr[data-kind=classpaper]").filter({ hasText: `${CLASS} · class practice` }).getByRole("link").click();
  // (the spare is a row of the pack's table, named as one: goals/uxn4-papers-to-approve.yaml)
  await expect(page.getByRole("main").locator("tbody").getByText("to approve", { exact: true })).toHaveCount(3);
  await expect(page.getByRole("main").locator("tbody tr").filter({ hasText: "Spare copy" })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Approve 2 papers and 1 spare" })).toBeEnabled();
});

test("the question bank is one number wherever it is named", async ({ page }) => {
  // the questions the engine can draw: made by it, active, of a skill at one of that skill's levels
  const [{ bank, taught }] = await sql<{ bank: number; taught: number }[]>`
    select count(*)::int as bank,
           count(*) filter (where exists (select 1 from child k where k.tenant_id = s.tenant_id and k.active
                                          and skill_taught_in(s.tenant_id, s.code, k.section)))::int as taught
    from item i join skill s on s.tenant_id = i.tenant_id and s.code = i.skill_set_code
    where i.source = 'generated' and i.status = 'active' and s.difficulty ? i.difficulty`;
  const words = (n: number) => n.toLocaleString("en-IN");

  await page.goto("/workflows");
  await expect(page.locator('[data-measure="N2"]')).toContainText(words(bank));

  await page.goto("/library");
  await expect(page.getByRole("main")).toContainText(`${words(taught)} questions ready to print`);
  await expect(page.getByRole("main"), "a part names the whole").toContainText(`of the bank's ${words(bank)}`);

  // Curriculum: its grades' questions are the bank's, each level counted at the grade that holds it
  await page.goto("/?details=1");
  const grades = page.getByRole("table", { name: "The curriculum, grade by grade" }).locator('tbody tr[data-depth="0"]');
  await expect(grades.first()).toBeVisible();
  const counts = await grades.locator("td:nth-child(2)").allInnerTexts();
  expect(counts.reduce((n, c) => n + number(c), 0), "Curriculum's grades add up to the bank").toBe(bank);
});

test("the worksheet library's total, pager and list are the same worksheets", async ({ page }) => {
  await page.goto("/worksheets");
  const library = page.locator("#library");
  const aside = await library.locator(".panel-head").first().innerText();
  const total = number(aside.split("worksheets")[0]);
  expect(total).toBeGreaterThan(0);
  const pager = library.getByText(/\d[\d,]* of [\d,]+/).first();
  await expect(pager, "the pager counts what the total counts").toContainText(`of ${total.toLocaleString("en-IN")}`);
  // the last page lists what is left: nothing is counted that the list never shows (read once the list has streamed in)
  const list = library.getByRole("table", { name: "Worksheets", exact: true }).locator("tbody tr");
  await expect(list.first()).toBeVisible();
  const per = await list.count();
  const last = Math.ceil(total / per);
  await page.goto(`/worksheets?page=${last}#library`);
  await expect(page.locator("#library").getByRole("table", { name: "Worksheets", exact: true }).locator("tbody tr")).toHaveCount(
    total - per * (last - 1),
  );
});
