/**
 * U7 — the parent report (goals/w4c-parent-report.yaml).
 *
 * One Grade 2 child, Tara: 2-digit + 1-digit nine of nine, and 2-digit − 2-digit on a paper with the smaller digit
 * taken from the larger four times. The copy's engine has no model key, and the report's prompt is not yet active,
 * so a model never writes here: the test keeps a draft of its own, written only from the facts the engine gives, and
 * checks what a parent reads — the name put in for [child], the counts beside the words, the child's own example, the
 * draft mark until an educator approves it in their name, and "out of date" once more answers are signed off.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U7-TEST";

async function tara(): Promise<string> {
  const [had] = await sql<
    { id: string }[]
  >`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (had) return had.id;
  return (await sql.begin(async (sql) => {
    const [{ tenant_id }] = await sql<
      { tenant_id: string }[]
    >`select id as tenant_id from tenant limit 1`;
    const [{ id }] = await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G2') returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, 'Tara')`;
    const [{ template }] = await sql<{ template: string }[]>`
      insert into sheet_template (tenant_id, band, child_id, week) values (${tenant_id}, 'G2', ${id}, ${SECTION}) returning id as template`;
    const [{ instance }] = await sql<{ instance: string }[]>`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
      values (${tenant_id}, ${`U7-TEST-${id.slice(0, 8)}`}, ${template}, ${id}, 'returned') returning id as instance`;
    const [{ capture }] = await sql<{ capture: string }[]>`
      insert into capture (tenant_id, path, pages, sheet_instance_id, status)
      values (${tenant_id}, 'u7-test', 1, ${instance}, 'processed') returning id as capture`;
    for (let n = 0; n < 4; n++) {
      const [{ item }] = await sql<{ item: string }[]>`
        insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses)
        values (${tenant_id}, ${`u7-test/${id.slice(0, 8)}/${n}`}, 'u7-test', 'R24', '{NUM.OPS.02}', 'Procedural', 'column',
                ${sql.json({ op: "-", a: 62, b: 27 })}, ${sql.json([{ rid: "a", answer: 35 }])}) returning id as item`;
      const [{ result }] = await sql<{ result: string }[]>`
        insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, misconception_codes, working_shown, state)
        values (${tenant_id}, ${capture}, ${item}, 'a', ${JSON.stringify({ child_answer: "45" })}, 'wrong',
                '{M_SMALL_FROM_LARGE}', 'none', 'confirmed') returning id as result`;
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    item_result_id, observed_at, confirmed_by)
        values (${tenant_id}, ${id}, 'NUM.OPS.02', 'R24', false, '{M_SMALL_FROM_LARGE}', 'item', ${result}, now(), 'e2e')`;
    }
    for (let n = 0; n < 9; n++)
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant_id}, ${id}, 'NUM.OPS.01', 'R21', true, '{}', 'item', now(), 'e2e')`;
    await sql`select rebuild_child_skill_state(${id}::uuid)`;
    return id;
  })) as string;
}

type Facts = {
  can_do: { id: string }[];
  nearly: { id: string }[];
  improving: { id: string }[];
  working_on: { id: string }[];
};

async function facts(id: string): Promise<Facts> {
  const r = await fetch(
    `http://127.0.0.1:${ENGINE_PORT}/child/${id}/parent-report`,
    {
      headers: { "X-Engine-Key": process.env.E2E_ENGINE_KEY! },
    },
  );
  return (await r.json()).facts;
}

/** A draft of the test's own, written from the facts alone and naming the child only as [child]. */
async function keepDraft(id: string, f: Facts) {
  const draft = {
    summary:
      "[child] adds a 2-digit and a 1-digit number with confidence, and is learning to exchange in subtraction.",
    can_do: [...f.can_do, ...f.nearly, ...f.improving].map((s) => ({
      id: s.id,
      sentence: "[child] adds with confidence.",
    })),
    working_on: f.working_on.map((w) => ({
      id: w.id,
      explanation:
        "When the top digit is smaller, [child] takes the smaller digit from the larger instead of exchanging a ten.",
    })),
    at_home: [
      "Use ten spoons as a ten and swap them for single spoons when you need more ones.",
    ],
    next_at_school:
      "The educator shows [child] the exchange with rods before writing it down.",
  };
  await sql`
    insert into parent_note (tenant_id, child_id, week, body, prompt_version)
    select tenant_id, id, '2026-W40', ${JSON.stringify({ facts: f, draft })}, 1 from child where id = ${id}::uuid`;
}

let id = "";
test.beforeAll(async () => {
  id = await tara();
  await sql`delete from parent_note where child_id = ${id}::uuid`;
});
test.afterAll(async () => {
  await sql`delete from parent_note where child_id = ${id}::uuid`;
  await sql.end();
});

test("the report is reached from the child's page, and says when its writer has not passed its check", async ({
  page,
}) => {
  await page.goto(`/growth/${id}`);
  await page.getByRole("link", { name: "Parent report →" }).click();
  await expect(page).toHaveURL(`/growth/${id}/parent`);
  const [{ active }] = await sql<{ active: boolean }[]>`
    select coalesce(bool_or(active), false) as active from prompt where purpose = 'parent_report'`;
  if (!active) {
    await expect(page.getByRole("status").first()).toContainText(
      "has not passed its check yet",
    );
    await expect(
      page.getByRole("button", { name: "Write the report" }),
    ).toHaveCount(0);
  }
  await expect(
    page.getByText("No report has been written for Tara yet."),
  ).toBeVisible();
});

test("a parent reads a letter with the child's name, the counts beside the words and their own example", async ({
  page,
}) => {
  const f = await facts(id);
  expect(f.can_do.map((s) => s.id)).toContain("ADD.2D1D");
  await keepDraft(id, f);
  await page.goto(`/growth/${id}/parent`);
  const letter = page.getByTestId("parent-report");
  await expect(letter.getByRole("heading", { level: 1 })).toHaveText("Tara");
  await expect(letter).not.toContainText("[child]");
  await expect(
    letter.getByRole("region", { name: "How they are doing" }),
  ).toContainText("Tara adds a 2-digit");
  const can = letter.getByRole("region", { name: "What they can do" });
  await expect(can).toContainText("2-digit + 1-digit");
  await expect(can).toContainText("ready for the next step");
  // the count and the state are the page's, from the facts, never the model's words (v9 swapped two skills' counts)
  await expect(can.getByTestId("count").first()).toHaveText(
    /^\d+ of \d+ right — secure\.$/,
  );
  const slip = letter.getByRole("region", { name: "What they are working on" });
  await expect(slip).toContainText("62 − 27");
  await expect(slip).toContainText("Tara wrote");
  await expect(slip).toContainText("45");
  await expect(slip).toContainText("35");
  await expect(letter.getByRole("region", { name: "At home" })).toContainText(
    "ten spoons",
  );
  // from the rows, not a constant: the out-of-date test below signs one more off each run (evidence is append-only)
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from evidence_event where child_id = ${id}::uuid and confirmed_by is not null`;
  await expect(letter).toContainText(
    `${n} answers, each checked by an educator`,
  );
  // never a code, never "teacher"
  await expect(letter).not.toContainText(
    /\b(R\d{1,2}|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/,
  );
  await expect(letter).not.toContainText(/teacher/i);
  await expect(letter.getByTestId("draft-mark")).toBeVisible();
});

test("an educator approves it in their own name, once, and a report out of date says so", async ({
  page,
}) => {
  await page.goto(`/growth/${id}/parent`);
  await page
    .getByRole("button", { name: "Approve for Tara's parents" })
    .click();
  await expect(page).toHaveURL(`/growth/${id}/parent?approved=1`);
  const letter = page.getByTestId("parent-report");
  await expect(letter.getByTestId("draft-mark")).toHaveCount(0);
  await expect(letter.getByTestId("approval")).toContainText("Approved by");
  await expect(page.getByRole("button", { name: /^Approve/ })).toHaveCount(0);

  // one more answer signed off: the approved report no longer matches the answers
  await sql`
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                observed_at, confirmed_by)
    select tenant_id, id, 'NUM.OPS.01', 'R21', true, '{}', 'item', now(), 'e2e' from child where id = ${id}::uuid`;
  await page.goto(`/growth/${id}/parent`);
  await expect(page.getByText("out of date")).toBeVisible();
});

test("the letter reads on a phone without pushing the page sideways", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/growth/${id}/parent`);
  await expect(page.getByTestId("parent-report")).toBeVisible();
  const sideways = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(sideways).toBe(false);
});
