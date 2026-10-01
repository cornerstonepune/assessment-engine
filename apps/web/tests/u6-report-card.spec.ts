/**
 * U6 — a child's report card (goals/u6-report-card.yaml).
 *
 * One Grade 2 child, Ria, with answers chosen so every part of the card has something true to say: 2-digit − 2-digit
 * on a real paper — the smaller digit taken from the larger four times (once with working), two right, one blank — so
 * it is red with her own example; 2-digit + 1-digit nine of nine right, so it is green; 2-digit + 2-digit five of eight,
 * three wrong no named mistake explains, so it is amber. Every number the test expects is read from the rows, never
 * from the code it checks. Evidence is append-only, so the child is made once and kept.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U6-TEST";
const COLOUR: Record<string, string> = {
  patterned_error: "red",
  emerging: "red",
  practising: "amber",
  secure: "green",
  stretch_ready: "green",
  not_enough_yet: "grey",
};

type Paper = {
  right: boolean | null;
  wrote: string;
  mistakes: string[];
  working: string;
};
const ON_PAPER: Paper[] = [
  ...Array<Paper>(3).fill({
    right: false,
    wrote: "45",
    mistakes: ["M_SMALL_FROM_LARGE"],
    working: "none",
  }),
  {
    right: false,
    wrote: "45",
    mistakes: ["M_SMALL_FROM_LARGE"],
    working: "partial",
  },
  ...Array<Paper>(2).fill({
    right: true,
    wrote: "35",
    mistakes: [],
    working: "none",
  }),
  { right: null, wrote: "", mistakes: [], working: "none" },
];

async function ria(): Promise<string> {
  const [had] = await sql<
    { id: string }[]
  >`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (had) return had.id;
  // all or nothing: a run that fails half way leaves no child the next run would take as made
  return (await sql.begin(async (sql) => {
    const [{ tenant_id }] = await sql<
      { tenant_id: string }[]
    >`select id as tenant_id from tenant limit 1`;
    const [{ id }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G2') returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, 'Ria')`;
    const [{ template }] = await sql<{ template: string }[]>`
    insert into sheet_template (tenant_id, band, child_id, week) values (${tenant_id}, 'G2', ${id}, ${SECTION}) returning id as template`;
    const [{ instance }] = await sql<{ instance: string }[]>`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
    values (${tenant_id}, ${`U6-TEST-${id.slice(0, 8)}`}, ${template}, ${id}, 'returned') returning id as instance`;
    const [{ capture }] = await sql<{ capture: string }[]>`
    insert into capture (tenant_id, path, pages, sheet_instance_id, status)
    values (${tenant_id}, 'u6-test', 1, ${instance}, 'processed') returning id as capture`;
    for (const [n, a] of ON_PAPER.entries()) {
      // a test's own question, entered as an earlier paper's (`legacy`): the bank's checks are for the questions it
      // generates, and four tests' "generated" rows broke `engine audit` on the copy (2026-10-01)
      const [{ item }] = await sql<{ item: string }[]>`
      insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses, source)
      values (${tenant_id}, ${`u6-test/${id.slice(0, 8)}/${n}`}, 'u6-test', 'R24', '{NUM.OPS.02}', 'Procedural', 'column',
              ${sql.json({ op: "-", a: 62, b: 27 })}, ${sql.json([{ rid: "a", answer: 35 }])}, 'legacy') returning id as item`;
      const status = a.right === null ? "blank" : a.right ? "correct" : "wrong";
      const [{ result }] = await sql<{ result: string }[]>`
      insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, misconception_codes, working_shown,
                               state, confirmed_by, confirmed_at)
      values (${tenant_id}, ${capture}, ${item}, 'a', ${JSON.stringify({ child_answer: a.wrote })}, ${status}, ${a.mistakes},
              ${a.working}, 'confirmed', 'e2e', now()) returning id as result`;
      await sql`
      insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                  item_result_id, observed_at, confirmed_by)
      values (${tenant_id}, ${id}, 'NUM.OPS.02', 'R24', ${a.right}, ${a.mistakes}, 'item', ${result}, now(), 'e2e')`;
    }
    const direct: [string, string, boolean][] = [
      ...Array<[string, string, boolean]>(9).fill(["NUM.OPS.01", "R21", true]),
      ...Array<[string, string, boolean]>(5).fill(["NUM.OPS.01", "R22", true]),
      ...Array<[string, string, boolean]>(3).fill(["NUM.OPS.01", "R22", false]),
    ];
    for (const [skill, rung, right] of direct) {
      await sql`
      insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                  observed_at, confirmed_by)
      values (${tenant_id}, ${id}, ${skill}, ${rung}, ${right}, '{}', 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${id}::uuid)`;
    return id;
  })) as string;
}

// One right answer on a question of two skills: a sign-off writes a row per skill (`answer_evidence`), in the same
// batch, and the card counts the answer once (goals/p0-one-answer-counts-once.yaml). Added to a child made before.
async function twoSkills(id: string) {
  await sql`
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                item_result_id, observed_at, confirmed_by, created_at)
    select e.tenant_id, e.child_id, 'NUM.OPS.01', e.rung_code, true, '{}', 'item', e.item_result_id, e.observed_at,
           e.confirmed_by, e.created_at
    from evidence_event e
    where e.child_id = ${id}::uuid and e.correct and e.item_result_id is not null
      and not exists (select 1 from evidence_event x where x.child_id = e.child_id and x.skill_code = 'NUM.OPS.01'
                                                      and x.item_result_id is not null)
    order by e.item_result_id limit 1`;
  await sql`select rebuild_child_skill_state(${id}::uuid)`;
}

let id = "";
test.beforeAll(async () => {
  id = await ria();
  await twoSkills(id);
  await waiting("remove"); // a run that stopped half way left one
});
test.afterAll(async () => {
  await waiting("remove");
  await sql.end();
});

test("the skill map places the grade's skill sets and one step either side, coloured by the graph's own state", async ({
  page,
}) => {
  await page.goto(`/growth/${id}`);
  await page.getByRole("link", { name: "Report card →" }).click();
  await expect(page).toHaveURL(`/growth/${id}/report`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Ria");

  const map = page.getByRole("img", { name: "Skill map" });
  // every Grade 2 skill set; in each lane (the registry skill a rung practises) the last Grade 1 and the first Grade 3
  // skill set on the ladder; and any the child has answers on
  const sets = await sql<{ code: string }[]>`
    with taught as (
      select ss.code, left(r.band, 2) as band, r.skill_codes[1] as lane, r.ladder_order, r.code as rung
      from skill_set ss join topic t on t.code = ss.topic_code and t.taught join rung r on r.code = ss.rung_code
      where ss.status is distinct from 'retired'),
    ends as (
      select code, band, row_number() over (partition by lane, band order by ladder_order desc) as from_top,
             row_number() over (partition by lane, band order by ladder_order) as from_bottom
      from taught where ladder_order is not null)
    select code from taught where band = 'G2'
    union select code from ends where band = 'G1' and from_top = 1
    union select code from ends where band = 'G3' and from_bottom = 1
    union select code from taught where rung in (select placed_rung from evidence_placed where child_id = ${id}::uuid)`;
  expect(sets.length).toBeLessThan(20); // a map a laptop reads, not every skill of three grades
  const shown = await map
    .locator("g[data-node]")
    .evaluateAll((gs) => gs.map((g) => g.getAttribute("data-node")));
  expect(shown.sort()).toEqual(sets.map((s) => s.code).sort());

  const states = await sql<{ code: string; state: string }[]>`
    select ss.code, s.state from child_skill_state s join skill_set ss on ss.rung_code = s.rung_code
    join rung r on r.code = s.rung_code
    -- a skill set is coloured by the skills its own rung practises; another skill a question also tests is not it
    where s.child_id = ${id}::uuid and s.n_events > 0 and s.skill_code = any(r.skill_codes)`;
  expect(states.length).toBe(3);
  for (const s of states)
    await expect(map.locator(`g[data-node="${s.code}"]`)).toHaveAttribute(
      "data-rag",
      COLOUR[s.state],
    );
  await expect(map.locator('g[data-node="SUB.2D2D"]')).toHaveAttribute(
    "data-rag",
    "red",
  );
  await expect(map.locator('g[data-node="ADD.3D1D"]')).toHaveAttribute(
    "data-rag",
    "none",
  );
  // the school's ladder: each skill set leads to the next one up its lane
  await expect(map.locator('line[data-edge="ADD.2D1D>ADD.2D2D"]')).toHaveCount(
    1,
  );
  await expect(map.locator('line[data-edge="SUB.2D1D>SUB.2D2D"]')).toHaveCount(
    1,
  );
  await expect(map.locator('g[data-grade="G2"]')).toContainText("this year");
});

test("every number on the card is the signed-off answers', and it says when any still wait", async ({
  page,
}) => {
  const [n] = await sql<
    { right: number; wrong: number; working: number; blank: number }[]
  >`
    with answers as (
      -- counted from the answers themselves, not from evidence rows: one answer is one, whatever its question tests
      select case ir.status when 'correct' then true when 'wrong' then false end as correct,
             coalesce(ir.working_shown, 'none') as working
      from item_result ir join capture c on c.id = ir.capture_id join sheet_instance si on si.id = c.sheet_instance_id
      where si.child_id = ${id}::uuid and ir.state = 'confirmed' and c.superseded_by is null
      union all
      select e.correct, 'none' from evidence_event e
      where e.child_id = ${id}::uuid and e.item_result_id is null and e.confirmed_by is not null)
    select count(*) filter (where correct)::int as right,
           count(*) filter (where correct = false and working = 'none')::int as wrong,
           count(*) filter (where correct = false and working <> 'none')::int as working,
           count(*) filter (where correct is null)::int as blank
    from answers`;
  await page.goto(`/growth/${id}/report`);
  const every = page.getByRole("region", { name: "Every answer" });
  await expect(every.locator('li[data-signal="right"]')).toContainText(
    String(n.right),
  );
  await expect(
    every.locator('li[data-signal="wrong, with working"]'),
  ).toContainText(String(n.working));
  await expect(every.locator('li[data-signal="wrong"]')).toContainText(
    String(n.wrong),
  );
  await expect(every.locator('li[data-signal="left blank"]')).toContainText(
    String(n.blank),
  );
  await expect(page.getByRole("status")).toContainText(
    `signed off by an educator: ${ON_PAPER.length} answers on 1 paper`,
  );
  // no code of the engine's reaches a parent: no rung, skill or mistake code, and never "teacher"
  await expect(page.locator("main")).not.toContainText(
    /\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/,
  );
  await expect(page.locator("main")).not.toContainText(/teacher/i);

  // an answer read but not yet checked: it has no evidence, and the card says it waits
  await waiting("add");
  await page.reload();
  await expect(page.getByRole("status")).toContainText(
    `1 of ${ON_PAPER.length + 1} answers`,
  );
  await expect(page.getByRole("status")).toContainText(
    `counts only the ${ON_PAPER.length} signed off`,
  );
  await expect(every.locator('li[data-signal="right"]')).toContainText(
    String(n.right),
  );
  await waiting("remove");
});

async function waiting(what: "add" | "remove") {
  const key = `u6-test/${id.slice(0, 8)}/waiting`;
  if (what === "remove") {
    await sql`delete from item_result where item_id in (select id from item where item_key = ${key})`;
    await sql`delete from item where item_key = ${key}`;
    return;
  }
  const [c] = await sql<{ tenant_id: string; capture: string }[]>`
    select c.tenant_id, c.id as capture from capture c join sheet_instance si on si.id = c.sheet_instance_id
    where si.child_id = ${id}::uuid limit 1`;
  const [{ item }] = await sql<{ item: string }[]>`
    insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses, source)
    values (${c.tenant_id}, ${key}, 'u6-test', 'R24', '{NUM.OPS.02}', 'Procedural', 'column',
            ${sql.json({ op: "-", a: 81, b: 46 })}, ${sql.json([{ rid: "a", answer: 35 }])}, 'legacy') returning id as item`;
  await sql`
    insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, misconception_codes, working_shown, state)
    values (${c.tenant_id}, ${c.capture}, ${item}, 'a', ${JSON.stringify({ child_answer: "35" })}, 'correct', '{}', 'none', 'candidate')`;
}

test("what goes well is named first, with its score, and the habit of showing working", async ({
  page,
}) => {
  const [add] = await sql<
    { name: string }[]
  >`select name from skill_set where code = 'ADD.2D1D'`;
  await page.goto(`/growth/${id}/report`);
  const well = page.getByTestId("going-well");
  await expect(well).toContainText(add.name);
  await expect(well).toContainText("9 of 9 right");
  await expect(well).toContainText(
    "Ria showed working on 1 of 7 wrong answers",
  );
});

test("each mistake is named with her own example, and what happens next is clear for the educator and for parents", async ({
  page,
}) => {
  const [m] = await sql<{ name: string; repair_hint: string }[]>`
    select name, repair_hint from misconception where code = 'M_SMALL_FROM_LARGE' and op = '-'`;
  await page.goto(`/growth/${id}/report`);
  const mistake = page
    .getByTestId("working-on")
    .locator('li[data-mistake="M_SMALL_FROM_LARGE"]');
  await expect(mistake).toContainText(m.name);
  await expect(mistake).toContainText("4 times");
  await expect(mistake).toContainText("62 − 27");
  await expect(mistake).toContainText("45");
  await expect(mistake).toContainText("35");
  await expect(page.getByTestId("unexplained")).toContainText(
    "3 other wrong answers",
  );

  const school = page.getByRole("region", { name: "In class" });
  await expect(school).toContainText(m.repair_hint);
  const home = page.getByRole("region", { name: "At home" });
  await expect(home).toContainText("Try this one together: 62 − 27");
  await expect(home).toContainText("Ria wrote 45; the answer is 35");
  await expect(home).not.toContainText("blank"); // one blank is not a habit worth a line
});

test("the card reads on a phone without pushing the page sideways, and prints", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/growth/${id}/report`);
  await expect(
    page.getByRole("button", { name: "Print or save as PDF" }),
  ).toBeVisible();
  const sideways = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(sideways).toBe(false);
});
