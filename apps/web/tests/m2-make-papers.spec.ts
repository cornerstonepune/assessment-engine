/**
 * Make papers (goals/m1-make-papers.yaml): each class's home papers for the week, proposed by the engine from each
 * child's own map and approved by a teacher — one child or all at once; and a paper a teacher chooses for one child:
 * any skills, a level each, how many questions, seen before it prints.
 *
 * The class is the test's own: three Grade 2 children — one repeating a subtraction mistake, one secure in addition
 * (so stretched), one with too little work for a paper. Evidence is append-only, so the children are made once and
 * kept; the papers the test makes are removed.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { isoWeek } from "../lib/week";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "M2-TEST";

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

test("each class's home papers are proposed from each child's own map, one skill each, and approved in one click", async ({
  page,
}) => {
  await page.goto("/make");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Make papers");
  const row = page.getByRole("table", { name: "Home papers this week" }).locator("tbody tr").filter({ hasText: SECTION });
  await expect(row.locator("td[data-n=proposed]")).toHaveText("2");
  await row.getByRole("link", { name: "Open" }).click();
  await expect(page).toHaveURL(`/make/${SECTION}`);

  const table = page.getByRole("table", { name: "Each child's home paper" });
  // the repeated subtraction mistake: one skill, at a level whose questions can show the mistake
  const asha = table.locator("tbody tr").filter({ hasText: "Asha" });
  await expect(asha).toContainText("2-digit − 2-digit");
  await expect(asha).toContainText("the same mistake more than once");
  // secure in addition: stretched one level up
  const bina = table.locator("tbody tr").filter({ hasText: "Bina" });
  await expect(bina).toContainText(/2-digit \+ 2-digit · (Hard|Advance)/);
  // too little work yet: no paper, and it says so
  await expect(table.locator("tbody tr").filter({ hasText: "Chetan" })).toContainText("Not enough checked work yet");

  await page.getByRole("button", { name: "Approve all 2" }).click();
  await expect(page.getByRole("status")).toContainText("Approved 2");
  const made = await sql<{ approved_by: string; kind: string }[]>`
    select si.approved_by, si.kind from sheet_instance si join child c on c.id = si.child_id
    where c.section = ${SECTION} and si.week = ${isoWeek()}`;
  expect(made).toHaveLength(2);
  expect(new Set(made.map((m) => `${m.kind} ${m.approved_by}`))).toEqual(new Set([`focus ${TEST_STAFF.email}`]));
  await expect(asha).toContainText(`Approved by ${TEST_STAFF.name}`);
  await expect(page.getByRole("button", { name: /Approve all/ })).toHaveCount(0);
});

test("a teacher chooses skills, a level each and how many, sees the questions, and approves the paper", async ({ page }) => {
  await page.goto(`/make/${SECTION}`);
  await page.getByRole("table", { name: "Each child's home paper" }).locator("tbody tr").filter({ hasText: "Chetan" })
    .getByRole("link", { name: "Choose a paper" }).click();
  await expect(page).toHaveURL(`/make/custom?child=${ids.Chetan}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("A paper for Chetan");

  const form = page.getByRole("form", { name: "Choose the paper" });
  await form.getByLabel("Skill and level 1").selectOption("SUB.2D2D~Medium");
  await form.getByLabel("Questions 1").fill("5");
  await form.getByLabel("Skill and level 2").selectOption("ADD.2D1D~Easy");
  await form.getByLabel("Questions 2").fill("3");
  await form.getByRole("button", { name: "See the paper" }).click();

  const preview = page.getByRole("region", { name: "The paper" });
  await expect(preview.getByRole("list", { name: "2-digit − 2-digit · Medium" }).getByRole("listitem")).toHaveCount(5);
  await expect(preview.getByRole("list", { name: "2-digit + 1-digit · Easy" }).getByRole("listitem")).toHaveCount(3);
  await page.getByRole("button", { name: "Approve and print" }).click();
  await expect(page).toHaveURL(/\/worksheets\/CS[0-9A-F]{6}$/);
  const [paper] = await sql<{ kind: string; approved_by: string; n: number }[]>`
    select si.kind, si.approved_by, array_length(st.item_ids, 1) as n from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id where si.child_id = ${ids.Chetan}::uuid`;
  expect(paper).toEqual({ kind: "custom", approved_by: TEST_STAFF.email, n: 8 });
});

test("a paper the bank cannot fill says why, and nothing prints", async ({ page }) => {
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from item where status = 'active' and skill_set_code = 'SUB.1D1D' and difficulty = 'Medium'`;
  test.skip(n >= 40, "this level holds enough questions for any count");
  await page.goto(`/make/custom?child=${ids.Chetan}&a=SUB.1D1D~Medium~40`);
  await expect(page.getByRole("status")).toContainText(`only ${n} questions this child has not seen`);
  await expect(page.getByRole("button", { name: "Approve and print" })).toHaveCount(0);
});

test("Make papers and a class fit a phone", async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 860 });
  for (const url of ["/make", `/make/${SECTION}`, `/make/custom?child=${ids.Asha}`]) {
    await page.goto(url, { waitUntil: "networkidle" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `${url} must not scroll sideways`).toBeLessThanOrEqual(1);
  }
});
