/**
 * U2 — Children (goals/u2-children.yaml).
 *
 * A grade opens on its classes; a class is its children against every step of each skill, each cell the colour of
 * the graph's own state; a child's page opens on one sentence, then the knowledge graph, the mistakes that repeat,
 * the next paper the engine proposes with Approve, and every paper made for or read from the child.
 *
 * The class is the test's own: three Grade 2 children with checked answers chosen so each colour appears. Evidence
 * is append-only, so the children are made once and kept; the papers the test makes are removed.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";
import { isoWeek } from "../lib/week";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U2-TEST-B"; // answers on the taxonomy-shaped skills' rungs (ADR 0034)
const WEEK = "U2-TEST";

// The settled colours (BUILD-ORDER, "the website as the teacher's week"), written here so the test does not
// read them from the code it checks.
const COLOUR: Record<string, string> = {
  patterned_error: "red",
  emerging: "red",
  practising: "amber",
  secure: "green",
  stretch_ready: "green",
  not_enough_yet: "grey",
};

type Answer = [skill: string, rung: string, right: boolean, mistakes: string[]];
const CHILDREN: { roll: string; name: string; answers: Answer[] }[] = [
  {
    // subtraction with exchange: 2 of 8, the smaller digit from the larger four times → red, the mistake repeating;
    // 2-digit addition with one regrouping 5 of 8 → amber; without regrouping 9 of 9 → green; within 20, 2 answers → grey
    roll: "1",
    name: "Asha",
    answers: [
      ...Array<Answer>(4).fill(["NUM.OPS.02", "R24", false, ["M_SMALL_FROM_LARGE"]]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R24", false, []]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R24", true, []]),
      ...Array<Answer>(5).fill(["NUM.OPS.01", "R22", true, []]),
      ...Array<Answer>(3).fill(["NUM.OPS.01", "R22", false, []]),
      ...Array<Answer>(9).fill(["NUM.OPS.01", "R21", true, []]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R20", true, []]),
    ],
  },
  { roll: "2", name: "Bina", answers: [] },
  { roll: "3", name: "Chetan", answers: Array<Answer>(4).fill(["NUM.OPS.02", "R23", true, []]) },
];

async function engine(path: string, body: object) {
  const r = await fetch(`http://127.0.0.1:${ENGINE_PORT}${path}`, {
    method: "POST",
    headers: {
      "X-Engine-Key": process.env.E2E_ENGINE_KEY!,
      "content-type": "application/json",
      "Idempotency-Key": `u2-${path}-${Date.now()}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json();
}

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
  await sql`delete from prescription where child_id in (${children})`;
  // the children's papers, and the class's spare copies of the week, which name no child
  await sql`delete from sheet_instance where child_id in (${children}) or week = ${WEEK}`;
  await sql`delete from sheet_template where child_id in (${children})`;
  await sql`delete from sheet_template where week = ${WEEK}`;
}

let ids: Record<string, string> = {};
test.beforeAll(async () => {
  ids = await testClass();
  await clearUp();
  // the class's own paper for the week, proposed by the engine and not yet approved
  await engine("/week/prescribe", { section: SECTION, week: WEEK, skill_set: "SUB.2D2D" });
  await engine("/week/assemble", { section: SECTION, week: WEEK });
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

test("each grade opens on its classes, and a class is its children against every step in red, amber, green or grey", async ({
  page,
}) => {
  await page.goto("/growth");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Children");
  const grade = page.getByRole("region", { name: "Grade 2" });
  await grade.getByRole("link", { name: new RegExp(`^${SECTION}`) }).click();
  await expect(page).toHaveURL(`/growth/class/${SECTION}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(SECTION);

  // the columns are the taught skills someone in the class has a checked answer on — never a column nobody answered
  const steps = await sql<{ col: string }[]>`
    select distinct s.skill_code || '|' || s.rung_code as col
    from child_skill_state s join child c on c.id = s.child_id
    join skill_set ss on ss.rung_code = s.rung_code join topic t on t.code = ss.topic_code and t.taught
    where c.section = ${SECTION} and s.n_events > 0`;
  const grid = page.getByRole("table", { name: `${SECTION}: each child on each step` });
  const shown = await grid.locator("thead th[data-col]").evaluateAll((ths) => ths.map((t) => t.getAttribute("data-col")));
  expect(shown.sort()).toEqual(steps.map((s) => s.col).sort());
  // in the school's words: no rung, skill or mistake code reaches a teacher
  await expect(grid).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/);

  // every cell is the colour of the graph's own state for that child and skill, and its score; grey where there is none
  const states = await sql<{ child_id: string; col: string; state: string }[]>`
    select s.child_id, s.skill_code || '|' || s.rung_code as col, s.state
    from child_skill_state s join child c on c.id = s.child_id where c.section = ${SECTION}`;
  for (const c of CHILDREN) {
    const row = grid.locator(`tbody tr[data-child="${ids[c.name]}"]`);
    await expect(row.getByRole("link", { name: c.name })).toHaveAttribute("href", `/growth/${ids[c.name]}`);
    for (const col of shown) {
      const state = states.find((s) => s.child_id === ids[c.name] && s.col === col)?.state ?? "not_enough_yet";
      await expect(row.locator(`td[data-col="${col}"]`)).toHaveAttribute("data-rag", COLOUR[state]);
    }
  }
  // the four colours are there, as the test's answers made them
  const asha = grid.locator(`tbody tr[data-child="${ids.Asha}"]`);
  for (const [col, rag] of [
    ["NUM.OPS.02|R24", "red"],
    ["NUM.OPS.01|R22", "amber"],
    ["NUM.OPS.01|R21", "green"],
    ["NUM.OPS.02|R20", "grey"],
  ]) {
    await expect(asha.locator(`td[data-col="${col}"]`)).toHaveAttribute("data-rag", rag);
  }
  await expect(asha.locator(`td[data-col="NUM.OPS.02|R24"]`)).toContainText("2/8");
});

test("a child's page opens on one plain sentence that counts what their answers show", async ({ page }) => {
  // not yet: the taught skills of the grade no checked answer of hers has reached
  const [{ notYet }] = await sql<{ notYet: number }[]>`
    select count(*)::int as "notYet" from skill_set ss
    join topic t on t.code = ss.topic_code and t.taught join rung r on r.code = ss.rung_code
    where r.band = 'G2' and not exists (select 1 from child_skill_state s
      where s.child_id = ${ids.Asha}::uuid and s.rung_code = r.code and s.n_events > 0)`;
  await page.goto(`/growth/${ids.Asha}`);
  await expect(page.getByTestId("summary")).toHaveText(
    `Asha needs help on 1 skill, is practising 1 and has got 1; 1 skill has too few answers to say; ${notYet} skill${notYet === 1 ? "" : "s"} of the grade not assessed yet.`,
  );
  // the sentence counts the skills shown beneath it, one line each
  const shown = page.getByRole("region", { name: "What their answers show" });
  for (const [rag, n] of [
    ["red", 1],
    ["amber", 1],
    ["green", 1],
    ["grey", 1],
  ] as const) {
    await expect(shown.locator(`li[data-rag="${rag}"]`)).toHaveCount(n);
  }

  await page.goto(`/growth/${ids.Bina}`);
  await expect(page.getByTestId("summary")).toHaveText(
    "Bina has no checked answers yet; this fills in once a paper is read and checked.",
  );
});

test("a child's page never draws a wall of grey, only skills with answers get a line, the rest are named once", async ({
  page,
}) => {
  await page.goto(`/growth/${ids.Asha}`);
  const shown = page.getByRole("region", { name: "What their answers show" });
  await expect(shown.locator("li[data-skill]")).toHaveCount(4);
  await expect(shown.getByTestId("not-yet")).toContainText("Not assessed yet:");
  // a line opens to the answers behind it (this test's answers were entered straight onto the graph, not read from a
  // paper, so it says where they are rather than showing a table; screens.spec.ts opens real ones)
  const red = shown.locator('li[data-rag="red"]');
  await expect(red).toContainText("2 of 8 right");
  await red.locator("summary").click();
  await expect(red.locator("details")).toHaveAttribute("open", "");
  await expect(red).toContainText("papers not yet re-read");
});

test("a child's page shows what their answers show and every mistake that repeats, and how often", async ({ page }) => {
  await page.goto(`/growth/${ids.Asha}`);
  const shown = page.getByRole("region", { name: "What their answers show" });
  await expect(shown.getByRole("heading", { name: "Addition & subtraction" })).toBeVisible();
  const [{ name: skill }] = await sql<{ name: string }[]>`select name from skill_set where code = 'SUB.2D2D'`;
  await expect(shown.locator('li[data-skill="SUB.2D2D"]')).toContainText(skill);

  const [{ name }] = await sql<{ name: string }[]>`select name from misconception where code = 'M_SMALL_FROM_LARGE' limit 1`;
  const mistakes = page.getByRole("region", { name: "Repeated mistakes" });
  const it = mistakes.getByRole("listitem").filter({ hasText: name });
  await expect(it).toBeVisible();
  await expect(it).toContainText("Subtraction · 2-digit − 2-digit");
  await expect(it).toContainText("4 times");
  await expect(mistakes.getByRole("listitem")).toHaveCount(1);

  await page.goto(`/growth/${ids.Chetan}`);
  await expect(page.getByRole("region", { name: "Repeated mistakes" })).toContainText(
    "No mistake has come back twice on the checked papers.",
  );
});

test("the engine proposes the next paper and a teacher approves it, once, in their own name", async ({ page }) => {
  await page.goto(`/growth/${ids.Asha}`);
  const next = page.getByRole("region", { name: "Next paper, proposed by the engine" });
  await expect(next.getByRole("list", { name: "Areas the next paper works on" }).getByRole("listitem").first()).toBeVisible();
  await next.getByRole("button", { name: "Approve this paper" }).click();
  await expect(page).toHaveURL(/\?paper=CS[0-9A-F]{6}$/);
  const qr = new URL(page.url()).searchParams.get("paper")!;

  const [made] = await sql<{ approved_by: string; print_status: string }[]>`
    select approved_by, print_status from sheet_instance where qr_code = ${qr}`;
  expect(made).toEqual({ approved_by: TEST_STAFF.email, print_status: "printed" });

  // once approved, the panel says who approved it and offers no second paper this week
  await page.goto(`/growth/${ids.Asha}`);
  await expect(next).toContainText(`Approved by ${TEST_STAFF.name}`);
  await expect(next.getByRole("link", { name: qr })).toHaveAttribute("href", `/worksheets/${qr}`);
  await expect(next.getByRole("button", { name: "Approve this paper" })).toHaveCount(0);

  // a child with nothing to work on is told so, with nothing to approve
  await page.goto(`/growth/${ids.Chetan}`);
  await expect(next.getByRole("button", { name: "Approve this paper" })).toHaveCount(0);
});

test("a child's page lists every paper made for them or read from them, with its purpose and who approved it", async ({
  page,
}) => {
  // the child's next paper, approved in the engine by the test's teacher unless the test before did it on the page
  const [had] = await sql`select 1 from sheet_instance where child_id = ${ids.Asha}::uuid and kind = 'focus'`;
  if (!had) await engine(`/child/${ids.Asha}/focus`, { week: isoWeek(), by: TEST_STAFF.email });
  const rows = await sql<{ qr_code: string; kind: string; approved_by: string | null }[]>`
    select qr_code, kind, approved_by from sheet_instance where child_id = ${ids.Asha}::uuid`;
  expect(rows.map((r) => r.kind).sort()).toEqual(["focus", "practice"]);
  await page.goto(`/growth/${ids.Asha}`);
  const papers = page.getByRole("region", { name: "Their papers" });
  await expect(papers.getByRole("listitem")).toHaveCount(rows.length);
  for (const r of rows) {
    const it = papers.getByRole("listitem").filter({ hasText: r.qr_code });
    await expect(it).toContainText(r.kind === "focus" ? "their own next paper" : "class practice");
    await expect(it).toContainText(r.approved_by ? `approved by ${TEST_STAFF.name}` : "waiting for a teacher to approve");
  }
});

test("the class and a child's page fit a phone, with the class's own answers on them", async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 860 });
  for (const url of ["/growth", `/growth/class/${SECTION}`, `/growth/${ids.Asha}`]) {
    await page.goto(url, { waitUntil: "networkidle" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `${url} must not scroll sideways`).toBeLessThanOrEqual(1);
  }
});

test("a class reads the shared tree, topic by topic, each skill by its name, in the Curriculum's order", async ({ page }) => {
  const topics = await sql<{ name: string }[]>`
    select t.name from topic t where exists (
      select 1 from skill_set s join level_rule l on s.rung_code = any(l.rung_codes)
      where s.topic_code = t.code and l.band = 'G2') order by t.ord`;
  await page.goto(`/growth/class/${SECTION}`);
  const grid = page.getByRole("table", { name: `${SECTION}: each child on each step` });
  const heads = await grid.locator("thead tr").first().locator("th").allInnerTexts();
  // after the "Child" column, the topics in their order (a topic shows only if the class has a step in it)
  const shown = heads.slice(1).map((h) => h.trim().toLowerCase());
  expect(shown).toEqual(topics.map((t) => t.name.toLowerCase()).filter((t) => shown.includes(t)));
  expect(shown.length).toBeGreaterThan(0);
  const [{ name }] = await sql<{ name: string }[]>`select name from skill_set where code = 'ADD.2D2D'`;
  await expect(grid.locator("thead tr").nth(1)).toContainText(name);
});
