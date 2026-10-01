/**
 * Step 4 — the validation queue (goals/s4-validation-queue.yaml).
 *
 * Nimish, 2026-09-21: "I'm not even able to see what all validations you need from our side to do for
 * the 200-odd questions that need to be validated. Why am I not even seeing that here?" Every answer the
 * engine is unsure of, one at a time, settled in a click — each test puts the answer back afterwards.
 *
 * The papers are the test's own (tests/rows.ts): a class of three read on one worksheet, every kind of answer the queue
 * holds on Asha's first paper, nothing waiting on her second, two waiting on Bina's, and Chitra's for the spot-check
 * alone. They were live's own until 2026-10-01, and nine tests skipped themselves on any database without them
 * (goals/p1-browser-tests-in-ci.yaml).
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper, aWorksheet } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

const ME = "e2e@cornerstone.test";
const HELD = { wrong: "read as a wrong answer; a person checks every wrong answer before it counts", blank: "read as blank; a person checks every blank before it counts" };
test.beforeAll(async () => {
  const kids = await aClass(sql, "S4-TEST", "G2", ["Asha", "Bina", "Chitra"]);
  const sums = ["46 + 38", "57 + 28", "68 + 27", "59 + 24", "35 + 47", "26 + 18", "33 + 29", "47 + 45"];
  const w = await aWorksheet(sql, {
    code: "S4-A", title: "S4 paper", date: "2026-09-01", band: "G2", week: "S4-TEST",
    items: [...sums.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })), { n: 9, page: 1, kind: "text", rung: "X1", question: "Which place did you regroup?" }],
  });
  const paper = (qr: string, child: string, reads: Parameters<typeof aReadPaper>[1]["reads"]) =>
    aReadPaper(sql, { qr, child, template: w.template, items: w.items, reads });
  await paper("S4TEST-1", kids.Asha, [
    { status: "unreadable", why: "not sure of the digits", guess: "84" },
    { status: "unreadable", why: "nothing it could read" },
    { status: "unreadable", why: "nothing it could read" },
    { status: "needs_teacher", read: "9 5" },
    { status: "needs_teacher", read: "73", why: HELD.wrong, guess: "73" },
    { status: "needs_teacher", why: HELD.blank },
    { status: "correct", read: "82" },
    { status: "unreadable", why: "3 numbers in the region for 1 answers" },
    { status: "needs_teacher", why: HELD.blank },
  ]);
  await paper("S4TEST-2", kids.Asha, [
    { status: "correct", read: "84", checkedBy: "rows.ts" },
    { status: "correct", read: "85" },
    { status: "wrong", read: "93", checkedBy: "rows.ts" },
    { status: "blank", checkedBy: "rows.ts" },
  ]);
  await paper("S4TEST-3", kids.Bina, [{ status: "unreadable" }, { status: "needs_teacher", read: "8 5" }]);
  // Settling an answer on a paper's own page signs the whole paper off (`resolve_result`), and a paper signed off has
  // no spot-check left: which of Asha's two kept one depended on an id's md5, and CI drew the one that had none.
  await paper("S4TEST-4", kids.Chitra, [{ status: "correct", read: "84" }, { status: "correct", read: "85" }, { status: "correct", read: "95" }]);
});

// every answer on a paper of the test's own; `waiting` counts the whole queue, as the screen does
const ALL = sql`from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null`;
const LIVE = sql`from item_result r join capture c on c.id = r.capture_id join item i on i.id = r.item_id
  where c.superseded_by is null and c.path like 'S4TEST-%'`;
const NUMBER = sql`coalesce(i.spec ->> 'answer', i.responses -> 0 ->> 'answer') is not null`;
// A wrong or a blank the engine holds for a person (ADR 0029) is a reading to confirm, not a judgement.
const notHeld = sql`coalesce(r.raw_read::jsonb ->> 'why', '') not like '%a person checks every%'`;

// The engine's own definition (`engine read waiting`), so the screen's count is checked against it.
const waiting = async () =>
  (await sql<{ n: number }[]>`select count(*)::int as n ${ALL} and r.status in ('unreadable', 'needs_teacher')`)[0].n;

type Row = { id: string; status: string; state: string; misconception_codes: string[]; working_shown: string };
const keep = async (id: string) =>
  (await sql<Row[]>`select id, status, state, misconception_codes, working_shown from item_result where id = ${id}`)[0];
async function putBack(r: Row) {
  await sql`delete from read_correction where item_result_id = ${r.id} and by = ${ME}`;
  await sql`update item_result set status = ${r.status}, state = ${r.state}, misconception_codes = ${r.misconception_codes},
            working_shown = ${r.working_shown} where id = ${r.id}`;
}

test("the queue counts what the engine counts, and shows each answer with the child's own writing", async ({ page }) => {
  const n = await waiting();
  await page.goto("/capture/check");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check the answers");
  await expect(page.getByText(`${n} answers left to check`)).toBeVisible();
  const writing = page.getByRole("img", { name: /^What .+ wrote for question/ });
  await expect.poll(() => writing.evaluate((i: HTMLImageElement) => i.naturalWidth), { timeout: 15_000 }).toBeGreaterThan(0);
  await expect(page.getByText("The question", { exact: true })).toBeVisible();
});

test("confirming the reader's guess settles the answer in the person's name, and the next one appears", async ({ page }) => {
  const [a] = await sql<{ id: string; guess: string }[]>`
    select r.id, r.raw_read::jsonb ->> 'guess' as guess ${LIVE} and r.status = 'unreadable' and r.state = 'candidate'
    and coalesce(r.raw_read::jsonb ->> 'guess', '') <> '' order by r.id limit 1`;
  expect(a, "an unclear reading with a guess").toBeTruthy();
  const before = await keep(a.id);
  const n = await waiting();
  try {
    await page.goto(`/capture/check?id=${a.id}`);
    await page.getByRole("button", { name: `Yes, the child wrote ${a.guess}` }).click();
    await expect.poll(async () => (await keep(a.id)).status, { timeout: 15_000 }).not.toBe("unreadable");
    const [said] = await sql`select human_read, by from read_correction where item_result_id = ${a.id}`;
    expect(said).toEqual({ human_read: a.guess, by: ME });
    await expect(page.getByText(`${n - 1} answers left to check`)).toBeVisible();
    await expect(page.locator(`a[href$="#a-${a.id}"]`)).toHaveCount(0);
  } finally {
    await putBack(before);
  }
});

test("typing what the child wrote marks it, and a blank is one press", async ({ page }) => {
  const rows = await sql<{ id: string }[]>`
    select r.id ${LIVE} and r.status = 'unreadable' and r.state = 'candidate' order by r.id desc limit 2`;
  expect(rows.length, "two unclear readings").toBe(2);
  const [typed, empty] = rows;
  const before = await Promise.all(rows.map((r) => keep(r.id)));
  try {
    await page.goto(`/capture/check?id=${typed.id}`);
    await page.getByLabel(/the child wrote/).fill("12");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect.poll(async () => (await keep(typed.id)).status, { timeout: 15_000 }).not.toBe("unreadable");
    expect((await sql`select human_read from read_correction where item_result_id = ${typed.id}`)[0].human_read).toBe("12");

    await page.goto(`/capture/check?id=${empty.id}`);
    await page.getByRole("button", { name: "Nothing is written here" }).click();
    await expect.poll(async () => (await keep(empty.id)).status, { timeout: 15_000 }).toBe("blank");
  } finally {
    for (const b of before) await putBack(b);
  }
});

test("judging one answer settles that answer only — nothing else on the paper is signed off", async ({ page }) => {
  const [a] = await sql<{ id: string; capture_id: string }[]>`
    select r.id, r.capture_id ${LIVE} and r.status = 'needs_teacher' and r.state = 'candidate'
    and r.raw_read::jsonb ->> 'answer_state' = 'written' and ${notHeld} order by r.id limit 1`;
  expect(a, "an answer waiting for a person's judgement").toBeTruthy();
  const before = await keep(a.id);
  const confirmed = async () =>
    (await sql`select count(*)::int as n from item_result where capture_id = ${a.capture_id} and state = 'confirmed'`)[0].n;
  const signedBefore = await confirmed();
  try {
    await page.goto(`/capture/check?id=${a.id}`);
    await page.getByRole("button", { name: "Wrong", exact: true }).click();
    await expect.poll(async () => (await keep(a.id)).status, { timeout: 15_000 }).toBe("wrong");
    expect((await keep(a.id)).state).toBe("candidate");
    expect(await confirmed()).toBe(signedBefore);
    // recorded as a judgement, never as a reading the reader's gold set would count (2026-09-21)
    const [row] = await sql`select by, judged from read_correction where item_result_id = ${a.id}`;
    expect(row).toMatchObject({ by: ME, judged: "wrong" });
  } finally {
    await putBack(before);
  }
});

// ADR 0029: a wrong or a blank on the engine's reading alone waits for a person. It is a reading to
// confirm, not a judgement to make, so it is asked the way a guess is and settles in one click.
for (const held of [
  { kind: "wrong", why: "read as a wrong answer%", says: "The engine read this as a wrong answer.", status: "wrong" },
  { kind: "blank", why: "read as blank%", says: "The engine found nothing written here.", status: "blank" },
]) {
  test(`a ${held.kind} the engine read is held for a person and settles in one click`, async ({ page }) => {
    const [a] = await sql<{ id: string; guess: string }[]>`
      select r.id, r.raw_read::jsonb ->> 'guess' as guess ${LIVE} and r.status = 'needs_teacher'
      and r.state = 'candidate' and r.raw_read::jsonb ->> 'why' like ${held.why} and ${NUMBER} order by r.id limit 1`;
    expect(a, `a ${held.kind} held for a person`).toBeTruthy();
    const before = await keep(a.id);
    try {
      await page.goto(`/capture/check?id=${a.id}`);
      await expect(page.getByText(held.says)).toBeVisible();
      await expect(page.getByRole("button", { name: "Right", exact: true })).toHaveCount(0);
      const confirm = held.kind === "blank" ? "Nothing is written here" : `Yes, the child wrote ${a.guess}`;
      await page.getByRole("button", { name: confirm }).click();
      await expect.poll(async () => (await keep(a.id)).status, { timeout: 15_000 }).toBe(held.status);
      const [said] = await sql`select human_read, by from read_correction where item_result_id = ${a.id}`;
      expect(said).toEqual({ human_read: held.kind === "blank" ? "" : a.guess, by: ME });
    } finally {
      await putBack(before);
    }
  });
}

// Nimish, 2026-09-22: "the system isn't taking text answers". An explanation the reader saw as blank was
// held; typing the child's words kept it held, Right and Wrong stayed hidden, and nine saves settled nothing.
test("an explanation held as blank takes the child's words, then asks for Right or Wrong", async ({ page }) => {
  const [a] = await sql<{ id: string; paper: string }[]>`
    select r.id, c.sheet_instance_id as paper ${LIVE} and r.state = 'candidate' and r.raw_read::jsonb ->> 'why' like 'read as blank%'
      and not ${NUMBER} and not exists (select 1 from read_correction rc where rc.item_result_id = r.id)
    order by r.id limit 1`;
  expect(a, "an explanation held as blank").toBeTruthy();
  const before = await keep(a.id);
  try {
    await page.goto(`/capture/${a.paper}`);
    const card = page.locator(`#a-${a.id}`);
    await card.getByRole("textbox").fill("because the number is big");
    await card.getByRole("button", { name: "Save" }).click();
    await expect(card.getByText("You said the child wrote because the number is big.")).toBeVisible();
    await card.getByRole("button", { name: "Right", exact: true }).click();
    await expect.poll(async () => (await keep(a.id)).status, { timeout: 15_000 }).toBe("correct");
  } finally {
    await putBack(before);
  }
});

test("on its paper, a held answer asks what the child wrote with the reading filled in, never Right or Wrong", async ({ page }) => {
  const [a] = await sql<{ id: string; paper: string; read: string }[]>`
    select r.id, c.sheet_instance_id as paper, r.raw_read::jsonb ->> 'child_answer' as read ${LIVE}
    and r.status = 'needs_teacher' and r.state = 'candidate' and r.raw_read::jsonb ->> 'why' like 'read as a wrong answer%'
    order by r.id limit 1`;
  expect(a, "a wrong answer held for a person").toBeTruthy();
  await page.goto(`/capture/${a.paper}`);
  const card = page.locator(`#a-${a.id}`);
  await expect(card.getByText(`The reader read ${a.read}, a wrong answer.`)).toBeVisible();
  await expect(card.getByRole("textbox")).toHaveValue(a.read);
  await expect(card.getByRole("button", { name: "Wrong", exact: true })).toHaveCount(0);
});

test("each paper has one spot-check, an answer the engine was sure of, asked the same way", async ({ page }) => {
  // The page's own rule: per paper, the settled answer with the smallest md5 of its id — shown while
  // it is still a candidate and no person has looked at it. Chitra's paper is the one no other test settles.
  const [spot] = await sql<{ id: string; read: string }[]>`
    select s.id, s.read from (
      select distinct on (c.sheet_instance_id) r.id, r.state, r.raw_read::jsonb ->> 'child_answer' as read ${LIVE}
      and c.path = 'S4TEST-4.pdf' and r.status in ('correct', 'wrong', 'blank')
      and r.raw_read::jsonb ->> 'answer_state' = 'written'
      order by c.sheet_instance_id, md5(r.id::text)) s
    where s.state = 'candidate' and not exists (select 1 from read_correction rc where rc.item_result_id = s.id)`;
  expect(spot, "Chitra's paper has its spot-check").toBeTruthy();
  await page.goto(`/capture/check?id=${spot.id}`);
  await expect(page.getByText("A spot-check: the engine was sure of this one.")).toBeVisible();
  await expect(page.getByRole("button", { name: `Yes, the child wrote ${spot.read}` })).toBeVisible();
});

test("a sheet shows its score as soon as nothing on it waits", async ({ page }) => {
  const [p] = await sql<{ right: number; scored: number; title: string; child: string }[]>`
    select count(*) filter (where r.status = 'correct')::int as right, min(si.child_id::text) as child,
           count(*) filter (where r.status in ('correct', 'wrong', 'blank'))::int as scored,
           min(t.key ->> 'title') as title
    from item_result r join capture c on c.id = r.capture_id and c.superseded_by is null
    join sheet_instance si on si.id = c.sheet_instance_id join sheet_template t on t.id = si.sheet_template_id
    where c.path like 'S4TEST-%'
    group by si.id having count(*) filter (where r.status in ('unreadable', 'needs_teacher')) = 0 limit 1`;
  expect(p, "a sheet with nothing waiting").toBeTruthy();
  await page.goto(`/capture?child=${p.child}`);
  await expect(page.getByText(`${p.right} / ${p.scored} right`).first()).toBeVisible();
});

// Nimish, 2026-09-22: "go student by student and within student — choose an assessment and then look at
// all questions within that". A child's page lists the papers read; each opens and steps to the next.
test("a child's papers open from their page, and each steps to the child's next paper", async ({ page }) => {
  const [c] = await sql<{ child_id: string; first: string; second: string; n: number }[]>`
    with p as (
      select si.child_id, si.id::text as id, count(*) over (partition by si.child_id)::int as n,
             row_number() over (partition by si.child_id order by t.key ->> 'date', si.created_at) as k
      from sheet_instance si join sheet_template t on t.id = si.sheet_template_id
      where exists (select 1 ${LIVE} and c.sheet_instance_id = si.id))
    select child_id, max(id) filter (where k = 1) as first, max(id) filter (where k = 2) as second, max(n) as n
    from p group by child_id having max(n) >= 2 order by child_id limit 1`;
  expect(c, "a child with two papers read").toBeTruthy();
  await page.goto(`/growth/${c.child_id}`);
  await page.locator(`a[href="/capture/${c.first}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/capture/${c.first}$`));
  await expect(page.getByText(new RegExp(`paper 1 of ${c.n}$`))).toBeVisible();
  await expect(page.getByRole("link", { name: "← Previous paper" })).toHaveCount(0);
  await page.getByRole("link", { name: "Next paper →" }).click();
  await expect(page).toHaveURL(new RegExp(`/capture/${c.second}$`));
  await expect(page.getByText(new RegExp(`paper 2 of ${c.n}$`))).toBeVisible();
  await expect(page.getByRole("link", { name: "← Previous paper" })).toHaveAttribute("href", `/capture/${c.first}`);
});

// Nimish, 2026-09-22: "a student's name. I click into the student, and then I have the papers … I click on
// the assessment, and then all the questions of that assessment appear". Capture & Mark is that, by class.
test("Capture & Mark lists students by class; a student lists their papers; a paper leads back to them", async ({ page }) => {
  const [c] = await sql<{ child: string; section: string; sheets: number }[]>`
    select si.child_id::text as child, min(ch.section) as section, count(distinct si.id)::int as sheets
    from sheet_instance si join child ch on ch.id = si.child_id
    where exists (select 1 ${LIVE} and c.sheet_instance_id = si.id)
    group by si.child_id order by si.child_id::text limit 1`;
  await page.goto("/capture");
  await expect(page.getByRole("heading", { name: c.section, exact: true }).first()).toBeVisible();
  await page.locator(`a[href="/capture?child=${c.child}"]`).click();
  await expect(page).toHaveURL(new RegExp(`child=${c.child}$`));
  const papers = page.getByRole("table").first().locator("tbody tr");
  await expect(papers).toHaveCount(c.sheets);
  await papers.first().getByRole("link").click();
  await expect(page.getByRole("heading", { name: "What this paper says, by skill" })).toBeVisible();
  await page.getByRole("link", { name: /’s papers$/ }).click();
  await expect(page).toHaveURL(new RegExp(`child=${c.child}$`));

  // the first student in the list steps to the next one with something left to check
  await page.goto("/capture");
  await page.getByRole("table").filter({ has: page.getByRole("link") }).first().getByRole("link").first().click();
  const first = new URL(page.url()).searchParams.get("child");
  await page.getByRole("link", { name: /^Next child to check: / }).click();
  await expect(page).not.toHaveURL(new RegExp(`child=${first}$`));
  await expect(page.getByRole("table").first().locator("tbody tr").first()).toBeVisible();
});

// ADR 0032: until the reader has earned 95% on a kind of question, a right answer waits too — its
// reading the one-click guess — and the queue says so in words.
test("a right answer of a kind the reader is not yet trusted on waits, and settles in one click", async ({ page }) => {
  const [a] = await sql<{ id: string; raw_read: string; read: string }[]>`
    select r.id, r.raw_read, r.raw_read::jsonb ->> 'child_answer' as read ${LIVE} and r.status = 'correct' and r.state = 'candidate'
      and coalesce(r.raw_read::jsonb ->> 'child_answer', '') <> ''
      and not exists (select 1 from read_correction rc where rc.item_result_id = r.id) order by r.id limit 1`;
  expect(a, "a right answer still a candidate").toBeTruthy();
  const before = await keep(a.id);
  try {
    const held = JSON.stringify({
      ...JSON.parse(a.raw_read),
      why: "read as a right answer; a person checks every answer of this kind until the reader is trusted on it (41 of the last 50 right)",
      guess: a.read,
    });
    await sql`update item_result set status = 'needs_teacher', raw_read = ${held} where id = ${a.id}`;
    await page.goto(`/capture/check?id=${a.id}`);
    await expect(page.getByText("This kind of question is not yet trusted (41 of the last 50 right)")).toBeVisible();
    await expect(page.getByRole("button", { name: "Right", exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: `Yes, the child wrote ${a.read}` }).click();
    await expect.poll(async () => (await keep(a.id)).status, { timeout: 15_000 }).toBe("correct");
  } finally {
    await sql`update item_result set raw_read = ${a.raw_read} where id = ${a.id}`;
    await putBack(before);
  }
});

test("the second reader's guess is offered back as one click, on the queue and on the paper", async ({ page }) => {
  const [a] = await sql<{ id: string; raw_read: string; paper: string }[]>`
    select r.id, r.raw_read, c.sheet_instance_id as paper ${LIVE} and r.state = 'candidate'
      and r.raw_read::jsonb ->> 'why' like '%numbers in the region%' and coalesce(r.raw_read::jsonb ->> 'guess', '') = ''
      and not exists (select 1 from read_correction rc where rc.item_result_id = r.id) order by r.id limit 1`;
  expect(a, "an answer the reader gave up on").toBeTruthy();
  try {
    const guessed = JSON.stringify({ ...JSON.parse(a.raw_read), guess: "282", guess_by: "read_with_examples with 3 of the child's answers" });
    await sql`update item_result set raw_read = ${guessed} where id = ${a.id}`;
    await page.goto(`/capture/check?id=${a.id}`);
    await expect(page.getByText(/The second reader, shown 3 of the child.s own answers, thinks the child wrote/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Yes, the child wrote 282" })).toBeVisible();
    await page.goto(`/capture/${a.paper}`);
    const card = page.locator(`#a-${a.id}`);
    await expect(card.getByText(/The second reader, shown 3 of the child's own answers, reads it as 282/)).toBeVisible();
    await expect(card.getByRole("textbox")).toHaveValue("282");
  } finally {
    await sql`update item_result set raw_read = ${a.raw_read} where id = ${a.id}`;
  }
});

test("Capture & Mark says how the reader is doing, with the database's own numbers", async ({ page }) => {
  const [n] = await sql<{ checked: number }[]>`
    with latest as (select distinct on (rc.item_result_id) rc.item_result_id, rc.judged from read_correction rc order by rc.item_result_id, rc.created_at desc)
    select count(*)::int as checked from item_result r join capture c on c.id = r.capture_id left join latest l on l.item_result_id = r.id
    where c.superseded_by is null and l.judged is null and (l.item_result_id is not null or r.state = 'confirmed')`;
  await page.goto("/capture");
  const panel = page.locator("section.panel", { has: page.getByRole("heading", { name: "How the reader is doing" }) });
  await expect(panel.getByText(`Checked by a person: ${n.checked} answers.`)).toBeVisible();
  // one table, by day first; each kind of question's standing is a click away (goals/u10-tables-read-straight.yaml)
  await expect(panel.getByRole("table")).toHaveCount(1);
  await panel.getByRole("button", { name: "By kind of question" }).click();
  await expect(panel.getByText(/a person checks every answer|trusted: settles alone/).first()).toBeVisible();
});

test("the queue is on the menu, and fits a phone", async ({ page }) => {
  // U1: the queue sits inside Papers (U9), and Today opens it
  await page.goto("/today");
  await page.getByRole("region", { name: "Answers to check" }).getByText(/Check them|Nothing waiting/).first().waitFor();
  await page.goto("/capture/check");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check the answers");
  await expect(page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "Papers" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await page.setViewportSize({ width: 400, height: 860 });
  await page.goto("/capture/check", { waitUntil: "networkidle" });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
