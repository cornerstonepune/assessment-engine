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
const SECTION = "U2-TEST";
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
      ...Array<Answer>(4).fill(["NUM.OPS.02", "R6", false, ["M_SMALL_FROM_LARGE"]]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R6", false, []]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R6", true, []]),
      ...Array<Answer>(5).fill(["NUM.OPS.01", "R5", true, []]),
      ...Array<Answer>(3).fill(["NUM.OPS.01", "R5", false, []]),
      ...Array<Answer>(9).fill(["NUM.OPS.01", "R4", true, []]),
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R3", true, []]),
    ],
  },
  { roll: "2", name: "Bina", answers: [] },
  { roll: "3", name: "Chetan", answers: Array<Answer>(4).fill(["NUM.OPS.02", "R4", true, []]) },
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

  // the steps are the grade's ladder, each rung once for every skill it carries, plus any step a child has answers on
  const steps = await sql<{ col: string }[]>`
    with rungs as (
      select unnest(rung_codes) as rung_code from level_rule where band = 'G2'
      union select rung_code from child_skill_state s join child c on c.id = s.child_id where c.section = ${SECTION}
    )
    select k || '|' || r.code as col from rungs x join rung r on r.code = x.rung_code, unnest(r.skill_codes) k
    union
    select s.skill_code || '|' || s.rung_code from child_skill_state s join child c on c.id = s.child_id
    where c.section = ${SECTION}`;
  const grid = page.getByRole("table", { name: `${SECTION}: each child on each step` });
  const shown = await grid.locator("thead th[data-col]").evaluateAll((ths) => ths.map((t) => t.getAttribute("data-col")));
  expect(shown.sort()).toEqual(steps.map((s) => s.col).sort());
  // in the school's words: no rung, skill or mistake code reaches a teacher
  await expect(grid).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/);

  // every cell is the colour of the graph's own state for that child and step, grey where there is none
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
    ["NUM.OPS.02|R6", "red"],
    ["NUM.OPS.01|R5", "amber"],
    ["NUM.OPS.01|R4", "green"],
    ["NUM.OPS.02|R3", "grey"],
  ]) {
    await expect(asha.locator(`td[data-col="${col}"]`)).toHaveAttribute("data-rag", rag);
  }
});

test("a child's page opens on one plain sentence that counts what the graph says", async ({ page }) => {
  await page.goto(`/growth/${ids.Asha}`);
  await expect(page.getByTestId("summary")).toHaveText(
    "Asha needs help on 1 step, is practising 1 and has got 1; 4 steps have too few answers to say.",
  );
  // the sentence counts the knowledge graph shown beneath it
  const graph = page.getByRole("region", { name: "Knowledge graph" });
  for (const [rag, n] of [
    ["red", 1],
    ["amber", 1],
    ["green", 1],
    ["grey", 4],
  ] as const) {
    await expect(graph.locator(`[data-rag="${rag}"]`)).toHaveCount(n);
  }

  await page.goto(`/growth/${ids.Bina}`);
  await expect(page.getByTestId("summary")).toHaveText(
    "Bina has no checked answers yet; the graph fills in once a paper is read and checked.",
  );
});

test("a child's page shows their knowledge graph and every mistake that repeats, and how often", async ({ page }) => {
  await page.goto(`/growth/${ids.Asha}`);
  const graph = page.getByRole("region", { name: "Knowledge graph" });
  await expect(graph.getByRole("heading", { name: "Addition" })).toBeVisible();
  await expect(graph.getByRole("heading", { name: "Subtraction" })).toBeVisible();

  const [{ name }] = await sql<{ name: string }[]>`select name from misconception where code = 'M_SMALL_FROM_LARGE' limit 1`;
  const mistakes = page.getByRole("region", { name: "Repeated mistakes" });
  const it = mistakes.getByRole("listitem").filter({ hasText: name });
  await expect(it).toBeVisible();
  await expect(it).toContainText("Subtraction · 2-digit subtraction with exchange");
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
