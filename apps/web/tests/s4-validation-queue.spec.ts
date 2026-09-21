/**
 * Step 4 — the validation queue (goals/s4-validation-queue.yaml).
 *
 * Nimish, 2026-09-21: "I'm not even able to see what all validations you need from our side to do for
 * the 200-odd questions that need to be validated. Why am I not even seeing that here?" Every answer the
 * engine is unsure of, one at a time, settled in a click — each test puts the answer back afterwards.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

const ME = "e2e@cornerstone.test";
const LIVE = sql`from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null`;

// The engine's own definition (`engine read waiting`), so the screen's count is checked against it.
const waiting = async () =>
  (await sql<{ n: number }[]>`select count(*)::int as n ${LIVE} and r.status in ('unreadable', 'needs_teacher')`)[0].n;

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
  test.skip(!a, "no unclear reading carries a guess yet");
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
    and r.raw_read::jsonb ->> 'answer_state' = 'written' order by r.id limit 1`;
  test.skip(!a, "no answer waits for a person's judgement");
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
    expect((await sql`select by from read_correction where item_result_id = ${a.id}`)[0].by).toBe(ME);
  } finally {
    await putBack(before);
  }
});

test("each paper has one spot-check, an answer the engine was sure of, asked the same way", async ({ page }) => {
  // The page's own rule: per paper, the settled answer with the smallest md5 of its id — shown while
  // it is still a candidate and no person has looked at it.
  const [spot] = await sql<{ id: string; read: string }[]>`
    select s.id, s.read from (
      select distinct on (c.sheet_instance_id) r.id, r.state, r.raw_read::jsonb ->> 'child_answer' as read ${LIVE}
      and r.status in ('correct', 'wrong', 'blank') and r.raw_read::jsonb ->> 'answer_state' = 'written'
      order by c.sheet_instance_id, md5(r.id::text)) s
    where s.state = 'candidate' and not exists (select 1 from read_correction rc where rc.item_result_id = s.id)
    limit 1`;
  await page.goto(`/capture/check?id=${spot.id}`);
  await expect(page.getByText("A spot-check: the engine was sure of this one.")).toBeVisible();
  await expect(page.getByRole("button", { name: `Yes, the child wrote ${spot.read}` })).toBeVisible();
});

test("a sheet shows its score as soon as nothing on it waits", async ({ page }) => {
  const [p] = await sql<{ right: number; scored: number; title: string }[]>`
    select count(*) filter (where r.status = 'correct')::int as right,
           count(*) filter (where r.status in ('correct', 'wrong', 'blank'))::int as scored,
           min(t.key ->> 'title') as title
    from item_result r join capture c on c.id = r.capture_id and c.superseded_by is null
    join sheet_instance si on si.id = c.sheet_instance_id join sheet_template t on t.id = si.sheet_template_id
    group by si.id having count(*) filter (where r.status in ('unreadable', 'needs_teacher')) = 0 limit 1`;
  test.skip(!p, "every sheet still has an answer waiting");
  await page.goto("/capture");
  await expect(page.getByText(`${p.right} / ${p.scored} right`).first()).toBeVisible();
});

test("the queue is on the menu, and fits a phone", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "Check answers" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check the answers");
  await expect(page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "Check answers" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await page.setViewportSize({ width: 400, height: 860 });
  await page.goto("/capture/check", { waitUntil: "networkidle" });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
