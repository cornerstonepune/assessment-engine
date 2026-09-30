/**
 * U8 — the Children table (goals/u8-children-table.yaml).
 *
 * Nimish, 2026-09-30, over the Children page's dot cards: "We have a proper tabular view here that outlines children
 * with their grades or something like that, and then that is clickable". Each grade is a table of its children, one
 * row each with their standing and next step, sortable by any column, and a click anywhere on a row opens the child.
 *
 * The class is the test's own, three Grade 2 children, made once and kept (evidence is append-only):
 * - roll 1 has a red skill, an amber one and a green one, a paper read on 21 Sep, and a report written before their
 *   answers were signed off, so it is out of date;
 * - roll 2 has nothing yet;
 * - roll 10 has one secure skill and an approved report.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U8-TEST";

type Answer = [skill: string, rung: string, right: boolean, mistakes: string[]];
const CHILDREN: { roll: string; name: string; answers: Answer[] }[] = [
  {
    roll: "1",
    name: "Asha",
    answers: [
      ...Array<Answer>(4).fill(["NUM.OPS.02", "R24", false, ["M_SMALL_FROM_LARGE"]]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R24", true, []]),
      ...Array<Answer>(5).fill(["NUM.OPS.01", "R22", true, []]),
      ...Array<Answer>(3).fill(["NUM.OPS.01", "R22", false, []]),
      ...Array<Answer>(9).fill(["NUM.OPS.01", "R21", true, []]),
    ],
  },
  { roll: "2", name: "Bina", answers: [] },
  { roll: "10", name: "Chetan", answers: Array<Answer>(6).fill(["NUM.OPS.02", "R23", true, []]) },
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
    // the reports before the answers they rest on: roll 1's, a draft, goes out of date; roll 10's is approved after
    if (c.roll === "1")
      await sql`insert into parent_note (tenant_id, child_id, week, body, created_at)
                values (${tenant_id}, ${id}, 'U8', '{"facts": {}, "draft": {}}', now() - interval '2 days')`;
    for (const [skill, rung, right, mistakes] of c.answers) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant_id}, ${id}, ${skill}, ${rung}, ${right}, ${mistakes}, 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${id}::uuid)`;
    if (c.roll === "10")
      await sql`insert into parent_note (tenant_id, child_id, week, body, approved_by, created_at)
                values (${tenant_id}, ${id}, 'U8', '{"facts": {}, "draft": {}}', 'e2e', now() + interval '1 minute')`;
    if (c.roll === "1") {
      const [{ id: tpl }] = await sql<{ id: string }[]>`
        insert into sheet_template (tenant_id, band, child_id, week) values (${tenant_id}, 'G2', ${id}, 'U8') returning id`;
      const [{ id: inst }] = await sql<{ id: string }[]>`
        insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
        values (${tenant_id}, ${"U8-" + id.slice(0, 8)}, ${tpl}, ${id}, 'returned') returning id`;
      await sql`insert into capture (tenant_id, path, pages, sheet_instance_id, status, created_at)
                values (${tenant_id}, 'u8', 1, ${inst}, 'processed', '2026-09-21 10:00+05:30')`;
    }
    ids[c.name] = id;
  }
  return ids;
}

let ids: Record<string, string> = {};
test.beforeAll(async () => {
  ids = await testClass();
});
test.afterAll(async () => sql.end());

const row = (page: Page, name: string) => page.locator(`tbody tr[data-child="${ids[name]}"]`);

test("each grade is a table of its children, each row their standing and next step in the school's words", async ({ page }) => {
  const [{ n: before }] = await sql<{ n: number }[]>`
    select count(*)::int as n from access_log where child_id = ${ids.Asha} and actor = ${TEST_STAFF.email}`;
  await page.goto("/growth");
  const grade = page.getByRole("region", { name: "Grade 2" });
  const table = grade.getByRole("table", { name: "Grade 2: every child" });
  await expect(table.locator("thead th")).toHaveText([
    /Roll/, /Name/, /Grade/, /Class/, /Needs help on/, /Secure/, /Practising/, /Last paper read/, /Parent report/,
  ]);

  // the skill roll 1 most needs help on is the red one, by its name; read from the tree, not from the page's code
  const [{ name: red }] = await sql<{ name: string }[]>`
    select ss.name from skill_set ss join topic t on t.code = ss.topic_code and t.taught where ss.rung_code = 'R24' limit 1`;
  const cells = (name: string) => row(page, name).locator("td");
  await expect(cells("Asha")).toHaveText(["1", "Asha", "Grade 2", SECTION, red, "1", "1", /21/, /out of date/]);
  await expect(cells("Bina")).toHaveText(["2", "Bina", "Grade 2", SECTION, "—", "0", "0", "—", "—"]);
  await expect(cells("Chetan")).toHaveText(["10", "Chetan", "Grade 2", SECTION, "—", "1", "0", "—", /approved/]);

  // in the school's words: no rung, skill or mistake code reaches a teacher
  await expect(table).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/);
  // each class still opens as its children against every skill
  await expect(grade.getByRole("link", { name: new RegExp(`^${SECTION}`) })).toHaveAttribute(
    "href",
    `/growth/class/${SECTION}`,
  );
  // names are read the one logged way
  const [{ n: after }] = await sql<{ n: number }[]>`
    select count(*)::int as n from access_log where child_id = ${ids.Asha} and actor = ${TEST_STAFF.email}`;
  expect(after).toBeGreaterThan(before);
});

test("a click anywhere on a child's row opens the child, and any column sorts the table", async ({ page }) => {
  await page.goto("/growth");
  const mine = async () =>
    (await page.locator(`tbody tr[data-section="${SECTION}"]`).evaluateAll((trs) => trs.map((t) => t.getAttribute("data-child"))));
  expect(await mine()).toEqual([ids.Asha, ids.Bina, ids.Chetan]); // by roll, 2 before 10

  // a sort is a new page, streamed in behind a skeleton: its column says it sorts before the rows are read
  const sorted = (label: string) => page.getByRole("table", { name: "Grade 2: every child" }).locator("th", { hasText: label });
  await page.getByRole("table", { name: "Grade 2: every child" }).getByRole("link", { name: "Secure" }).click();
  await expect(page).toHaveURL(/sort=secure/);
  await expect(sorted("Secure")).toHaveAttribute("aria-sort", "descending");
  expect((await mine()).slice(0, 2).sort()).toEqual([ids.Asha, ids.Chetan].sort()); // one secure skill each, then none
  expect((await mine())[2]).toBe(ids.Bina);

  await page.getByRole("table", { name: "Grade 2: every child" }).getByRole("link", { name: "Parent report" }).click();
  await expect(page).toHaveURL(/sort=report/);
  await expect(sorted("Parent report")).toHaveAttribute("aria-sort", "other"); // what needs doing first

  // a click where a person would click it: in the middle of the Practising cell, nowhere near the name, on screen
  const cell = row(page, "Bina").locator("td").nth(6);
  await cell.scrollIntoViewIfNeeded();
  const box = (await cell.boundingBox())!;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page).toHaveURL(`/growth/${ids.Bina}`);
});
