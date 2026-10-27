/**
 * U31 — topics are operations, and a class is taught skill by skill (goals/t1-topics-are-operations.yaml, ADR 0076).
 * Nimish, 2026-10-15, on live's Children page: "You are putting estimation word problems as a potential topic. How can
 * that be a topic? These are types of problems. The topics are core addition, subtraction, multiplication, division,
 * and factors."
 *
 * Curriculum holds six topics, by operation, and no kind of question among them. Inside a taught class, each skill of
 * a topic has its own switch: a class can be taught Multiplication and not yet its columns. No chip on Children or
 * Assessments names a kind of question, or a topic with nothing taught that a class's children can be given.
 *
 * One Grade 3 class of the test's own (tests/rows.ts); every word said of it is taken away after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U31-CLASS";
const SIX = ["Addition & subtraction", "Multiplication", "Division", "Multiples & factors", "Number sense", "Data handling"];
// what the topics were before (live's chips on 2026-10-15): each a kind of question or a slice of one operation
const KINDS = [
  "Estimation",
  "Word problems",
  "Number sense & strategies",
  "Reasoning",
  "Multiplication models",
  "Multiplication facts and place value",
  "Multiplication in columns",
  "Estimating products and quotients",
  "Stories with × and ÷",
  "Equations with × and ÷",
];

test.afterAll(async () => {
  await sql`delete from class_skill where section = ${CLASS}`;
  await sql.end();
});

test("curriculum lists the six topics, and a class is taught a topic from its row, every skill in it", async ({ page }) => {
  await aClass(sql, CLASS, "G3", ["Ruhi", "Sam"]);
  const topics = (await sql<{ name: string }[]>`select name from topic where subject_code = 'NUM' order by ord`).map((t) => t.name);
  expect(topics, "the maths has six topics, by operation").toEqual(SIX);
  const said = (skill: string) =>
    sql<{ t: boolean }[]>`select skill_taught_in(tenant_id, ${skill}, ${CLASS}) as t from skill where code = ${skill}`;
  expect((await said("MUL.2D1D"))[0].t, "column multiplication waits for an educator's word").toBe(false);
  try {
    // equal groups, Grade 1's, is taught by the school: so Multiplication is taught in the class, with one skill of it.
    // A skill is said taught for one class from its own row on Curriculum (tests/u40), the topic from its row on What needs doing.
    // The class is made not taught first, as a person's word once was (the page has no button to undo it).
    await sql`select say_taught(t.tenant_id, ${CLASS}, 'MUL', null, false, 'U31 test') from topic t where t.code = 'MUL'`;
    const left = await sql<{ n: number }[]>`
      select count(*)::int as n from skill s
      where s.topic_code = 'MUL' and skill_taught_in(s.tenant_id, s.code, ${CLASS})`;
    expect(left[0].n, "not one multiplication skill is taught in the class now").toBe(0);
    await page.goto(`/today?kind=taught&subject=NUM&class=${CLASS}`);
    const again = page.locator('tr[data-kind=taught][data-shows="Multiplication"]');
    if (await again.getByLabel("Class taught Multiplication").count()) await again.getByLabel("Class taught Multiplication").selectOption(CLASS);
    await again.getByRole("button", { name: "Mark as taught" }).click();
    await expect(page.getByRole("main")).toContainText(`Multiplication is taught in ${CLASS} now`);
    expect((await said("MUL.2D1D"))[0].t, "every skill of the topic, the columns too").toBe(true);
    const [who] = await sql<{ taught_by: string }[]>`
      select taught_by from class_skill where section = ${CLASS} and skill_set_code = 'MUL.2D1D'`;
    expect(who.taught_by, "in the name of who said it").toBe(TEST_STAFF.name);
  } finally {
    await sql`delete from class_skill where section = ${CLASS}`;
  }
});

test("no chip names a kind of question, or a topic with nothing taught at the class's grade", async ({ page }) => {
  // Children has none any more (goals/ux10-declutter.yaml); Assessments has the topics as one dropdown of its filter row
  for (const at of ["/papers"]) {
    await page.goto(at);
    const topic = page.locator('[data-filterbar] select[name="topic"]');
    await expect(topic.locator("option").first()).toHaveText("Every topic");
    const names = (await topic.locator("option").allInnerTexts()).map((n) => n.trim()).filter((n) => n !== "Every topic");
    expect(names.length, at).toBeGreaterThan(0);
    expect(names.filter((n) => !SIX.includes(n)), `${at}: a topic that is not one of the six`).toEqual([]);
    expect(names.filter((n) => KINDS.includes(n)), `${at}: a kind of question as a topic`).toEqual([]);
    // each topic has a skill taught somewhere that a class on the roll can be given: its grade or below
    const shown = await sql<{ name: string }[]>`
      select distinct t.name from topic t
      join skill s on s.tenant_id = t.tenant_id and s.topic_code = t.code
      join (select distinct section, band from child where active) k on skill_taught_in(s.tenant_id, s.code, k.section)
      where exists (select 1 from jsonb_object_keys(s.difficulty) lvl
                    where left(coalesce(s.level_band ->> lvl, s.grade), 2) <= left(k.band, 2))`;
    expect([...names].sort(), at).toEqual(shown.map((t) => t.name).sort());
  }
});
