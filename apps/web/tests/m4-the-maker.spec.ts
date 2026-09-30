/**
 * The maker (goals/m3-the-maker.yaml): class practice, class assessments and home assessments for any children of a
 * class — one paper for all, the same skill with different questions for each, or each child's own next step — in
 * one screen. Nimish, 2026-09-30: "That should be like an interface in itself".
 *
 * The class is the test's own: three Grade 2 children — one repeating a subtraction mistake, one secure in addition,
 * one with too little work for a paper of their own. Evidence is append-only, so the children are made once and
 * kept; the papers the test makes are removed.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "M4-TEST";

type Answer = [skill: string, rung: string, right: boolean, mistakes: string[]];
const CHILDREN: { roll: string; name: string; answers: Answer[] }[] = [
  {
    roll: "1",
    name: "Asha",
    answers: [
      ...Array<Answer>(4).fill(["NUM.OPS.02", "R24", false, ["M_SMALL_FROM_LARGE"]]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R24", false, []]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R24", true, []]),
    ],
  },
  { roll: "2", name: "Bina", answers: Array<Answer>(10).fill(["NUM.OPS.01", "R22", true, []]) },
  { roll: "3", name: "Chetan", answers: Array<Answer>(2).fill(["NUM.OPS.01", "R22", true, []]) },
];

async function testClass(): Promise<Record<string, string>> {
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const ids: Record<string, string> = {};
  for (const c of CHILDREN) {
    const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = ${c.roll}`;
    if (had) {
      ids[c.name] = had.id;
      continue;
    }
    const [{ id }] = await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, ${c.roll}, ${SECTION}, 'G2') returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, ${c.name})`;
    for (const [skill, rung, right, mistakes] of c.answers) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant_id}, ${id}, ${skill}, ${rung}, ${right}, ${mistakes}, 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${id}::uuid)`;
    ids[c.name] = id;
  }
  return ids;
}

async function clearUp() {
  const children = sql`select id from child where section = ${SECTION}`;
  await sql`delete from item_exposure where child_id in (${children})`;
  await sql`delete from sheet_instance where child_id in (${children})`;
  await sql`delete from sheet_template where child_id in (${children})`;
}

let ids: Record<string, string> = {};
test.beforeAll(async () => {
  ids = await testClass();
  await clearUp();
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

const CODES = /\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/;

test("an educator picks the kind, the children and the way, sees every paper, makes them, and prints them as one", async ({ page }) => {
  await page.goto("/papers");
  await page.getByRole("link", { name: "Make a paper" }).click();
  await expect(page).toHaveURL(/\/papers\/make$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Make papers");
  const form = page.getByRole("form", { name: "Choose the papers" });
  await form.getByLabel("Class").selectOption(SECTION);
  await form.getByRole("button", { name: "Show the class" }).click();

  // every child of the class is ticked to begin with; the educator leaves one out
  for (const name of ["Asha", "Bina", "Chetan"]) await expect(form.getByRole("checkbox", { name })).toBeChecked();
  await form.getByRole("radio", { name: /Class assessment/ }).check();
  await form.getByRole("radio", { name: /One paper for all/ }).check();
  await form.getByRole("checkbox", { name: "Chetan" }).uncheck();
  await form.getByLabel("Skill and level 1").selectOption("SUB.2D2D~Easy");
  await form.getByLabel("Questions 1").fill("5");
  await form.getByRole("button", { name: "See the papers" }).click();

  // every paper is seen before anything is made: the same five questions for both, and no one else
  const papers = page.getByRole("region", { name: "The papers" });
  const table = papers.getByRole("table", { name: "Each child's paper" });
  await expect(table.locator("tbody tr")).toHaveCount(2);
  await expect(table.locator("tbody tr").nth(0)).toContainText("Asha");
  await expect(table.locator("tbody tr").nth(1)).toContainText("Bina");
  await expect(papers.getByRole("list").first().getByRole("listitem")).toHaveCount(5);
  await expect(papers).not.toContainText(CODES);

  await papers.getByRole("button", { name: "Make and approve 2 papers" }).click();
  await expect(page.getByText("2 papers made and approved in your name.")).toBeVisible();
  const made = await sql<{ name: string; kind: string; approved_by: string; items: string }[]>`
    select p.first_name as name, si.kind, si.approved_by, t.item_ids::text as items
    from sheet_instance si join sheet_template t on t.id = si.sheet_template_id join pii.child p on p.child_id = si.child_id
    where si.section = ${SECTION} order by p.first_name`;
  expect(made.map((m) => [m.name, m.kind, m.approved_by])).toEqual([
    ["Asha", "assessment", TEST_STAFF.email],
    ["Bina", "assessment", TEST_STAFF.email],
  ]);
  expect(made[0].items).toBe(made[1].items); // one paper for all: the same questions on both copies

  // printed as one PDF
  const pdf = await page.request.get((await page.getByRole("link", { name: "Print them all" }).getAttribute("href"))!);
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()["content-type"]).toContain("application/pdf");
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");

  // and in Papers, ready to hand out
  await page.getByRole("link", { name: "See them in Papers" }).click();
  const list = page.getByRole("table", { name: "Every paper" });
  await expect(list.locator("tbody tr")).toHaveCount(2);
  await expect(list.locator("tbody tr").first()).toContainText("Class assessment");
  await expect(list.locator("tbody tr").first()).toContainText("printed");
});

test("each child's own next step is shown child by child, and a child with nothing to go on can be given a skill", async ({ page }) => {
  await page.goto(`/papers/make?class=${SECTION}`);
  const form = page.getByRole("form", { name: "Choose the papers" });
  await form.getByRole("radio", { name: /Home assessment/ }).check();
  await form.getByRole("radio", { name: /Each child's own next step/ }).check();
  await expect(form.getByLabel("Skill and level 1")).toBeHidden(); // each child's skill is their own
  await form.getByRole("button", { name: "See the papers" }).click();

  const row = (name: string) => page.locator(`table[aria-label="Each child's paper"] tr[data-child="${ids[name]}"]`);
  await expect(row("Asha")).toContainText("the same mistake more than once");
  await expect(row("Chetan")).toContainText("cannot be made");
  await expect(row("Chetan")).toContainText("no next step to go on yet");
  await expect(page.getByRole("button", { name: /Make and approve/ })).toBeDisabled();
  // the widest the screen gets — a change for every child — still fits a phone: the table scrolls, not the page
  await page.setViewportSize({ width: 400, height: 860 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, "the page must not scroll sideways").toBeLessThanOrEqual(1);
  await page.setViewportSize({ width: 1280, height: 800 });

  await page.getByLabel("Change Chetan's paper").selectOption(`${ids.Chetan}~ADD.2D2D~Easy`);
  await page.getByRole("button", { name: "See the papers with these changes" }).click();
  await expect(row("Chetan")).toContainText("Chosen by you.");
  await expect(row("Chetan")).toContainText("12 questions");
  await expect(row("Asha")).toContainText("the same mistake more than once"); // the others stay their own
  await page.getByRole("button", { name: "Make and approve 3 papers" }).click();
  await expect(page.getByText("3 papers made and approved in your name.")).toBeVisible();
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from sheet_instance where section = ${SECTION} and kind = 'focus' and approved_by = ${TEST_STAFF.email}`;
  expect(n).toBe(3);
});
