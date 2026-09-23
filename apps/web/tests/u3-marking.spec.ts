/**
 * U3 — Marking (goals/u3-marking.yaml).
 *
 * Capture & Mark and Check answers are one area: papers in, and every answer on them settled by the engine, checked
 * by a person or still waiting — by class, by child and by worksheet — with the queue inside it and how the reader
 * is doing. The counts are checked against the tables themselves, from the definition written out here, not against
 * the view the page reads.
 *
 * The class is the test's own: two Grade 2 children, three read papers of two worksheets. One paper is signed off,
 * which makes evidence, and evidence is append-only, so the class is made once and kept.
 */
import { expect, type Locator, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U3-TEST";

type Answer = [status: string, read: string, by?: "typed" | "judged"];
// Two papers, entered by the engine exactly as a real paper is (`engine legacy paper`): four sums and a question
// only a person can judge. Dev sat both, Esha the first; on Dev's first paper nothing waits and it is signed off.
const SUMS = ["46 + 38", "57 + 28", "68 + 27", "59 + 24"];
const WORKSHEETS = [
  { code: "U3-A", title: "U3 paper A", date: "2026-09-01" },
  { code: "U3-B", title: "U3 paper B", date: "2026-09-08" },
];
const PAPERS: { child: string; sheet: string; code: string; answers: Answer[]; signed?: boolean }[] = [
  {
    child: "Dev",
    sheet: "U3TEST-1",
    code: "U3-A",
    answers: [["correct", "84"], ["correct", "85"], ["correct", "95"], ["wrong", "73"], ["correct", "the tens", "judged"]],
    signed: true,
  },
  {
    child: "Dev",
    sheet: "U3TEST-2",
    code: "U3-B",
    answers: [["correct", "84"], ["correct", "85"], ["unreadable", ""], ["needs_teacher", "8 3"], ["correct", "95", "typed"]],
  },
  {
    child: "Esha",
    sheet: "U3TEST-3",
    code: "U3-A",
    answers: [["correct", "84"], ["correct", "85"], ["wrong", "85", "typed"], ["unreadable", ""], ["needs_teacher", "the ones"]],
  },
];

/** The engine enters a paper from its definition, as `engine legacy paper` always does; returns its question ids. */
function enterPaper(w: (typeof WORKSHEETS)[number]): void {
  const dir = mkdtempSync(path.join(tmpdir(), "u3-"));
  const file = path.join(dir, `${w.code}.json`);
  writeFileSync(
    file,
    JSON.stringify({
      ...w,
      band: "G2",
      week: SECTION,
      pages: [{ n: 1, mask: 0 }],
      items: [
        ...SUMS.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
        { n: 5, page: 1, kind: "text", rung: "X1", question: "Which place did you regroup?" },
      ],
    }),
  );
  execFileSync(path.resolve(__dirname, "../../../bin/engine"), ["legacy", "paper", file], {
    env: { ...process.env, DATABASE_URL: process.env.DATABASE_URL },
  });
  rmSync(dir, { recursive: true });
}

async function testClass(): Promise<Record<string, string>> {
  const kids: Record<string, string> = {};
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  for (const [roll, name] of [["1", "Dev"], ["2", "Esha"]]) {
    const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = ${roll}`;
    if (had) {
      kids[name] = had.id;
      continue;
    }
    const [{ id }] = await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, ${roll}, ${SECTION}, 'G2') returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, ${name})`;
    kids[name] = id;
  }
  const [made] = await sql`select 1 from sheet_instance where qr_code = 'U3TEST-1'`;
  if (made) return kids;
  for (const w of WORKSHEETS) enterPaper(w);
  for (const p of PAPERS) {
    const [t] = await sql<{ id: string; item_ids: string[] }[]>`
      select id, item_ids from sheet_template where source = 'legacy' and batch_id = ${p.code}`;
    const [{ id: sheet }] = await sql<{ id: string }[]>`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
      values (${tenant_id}, ${p.sheet}, ${t.id}, ${kids[p.child]}, 'returned') returning id`;
    const [{ id: cap }] = await sql<{ id: string }[]>`
      insert into capture (tenant_id, path, pages, status, sheet_instance_id)
      values (${tenant_id}, ${p.sheet + ".pdf"}, 1, 'processed', ${sheet}) returning id`;
    for (const [i, [status, read, by]] of p.answers.entries()) {
      const raw = JSON.stringify({ child_answer: read, answer_state: read ? "written" : "blank", why: read ? "" : "no number" });
      const [{ id }] = await sql<{ id: string }[]>`
        insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status)
        values (${tenant_id}, ${cap}, ${t.item_ids[i]}, 'a', ${raw}, ${status}) returning id`;
      if (by) {
        await sql`
          insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by, judged)
          values (${tenant_id}, ${kids[p.child]}, ${cap}, ${id}, ${read}, ${read}, 'e2e', ${by === "judged" ? status : null})`;
      }
    }
    if (p.signed) await sql`select confirm_results(${kids[p.child]}::uuid, 'e2e', ${cap}::uuid)`;
  }
  return kids;
}

// Where an answer stands, written out from the engine's rule: waiting while its status needs a person; checked by a
// person once a person typed, confirmed or judged it; otherwise settled by the engine.
const STANDING = sql`
  case when r.status in ('unreadable', 'needs_teacher') then 'waiting'
       when exists (select 1 from read_correction rc where rc.item_result_id = r.id) then 'person'
       else 'engine' end`;
type Counts = { papers: number; engine: number; person: number; waiting: number };
async function counts(where = sql`true`): Promise<Counts> {
  const [c] = await sql<Counts[]>`
    select count(distinct si.id)::int as papers,
           count(*) filter (where ${STANDING} = 'engine')::int as engine,
           count(*) filter (where ${STANDING} = 'person')::int as person,
           count(*) filter (where ${STANDING} = 'waiting')::int as waiting
    from item_result r join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id
    join child ch on ch.id = si.child_id join sheet_template t on t.id = si.sheet_template_id
    where c.superseded_by is null and ${where}`;
  return c;
}

/** The four numbers a row or the tiles show, by their labels. */
async function shown(scope: Locator): Promise<Counts> {
  const n = async (label: string) => Number((await scope.getByTestId(label).innerText()).replace(/\D/g, "") || 0);
  return { papers: await n("papers"), engine: await n("engine"), person: await n("person"), waiting: await n("waiting") };
}

let kids: Record<string, string> = {};
test.beforeAll(async () => {
  kids = await testClass();
});
test.afterAll(async () => sql.end());

test("marking is one area, and says how many papers are in and where every answer stands", async ({ page }) => {
  await page.goto("/capture");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Marking");
  const menu = page.getByRole("navigation", { name: "Sections" });
  await expect(menu.getByRole("link", { name: "Marking" })).toHaveAttribute("aria-current", "page");
  expect(await shown(page.getByRole("region", { name: "Where every answer stands" }))).toEqual(await counts());

  // checking answers is inside Marking, not a page of its own
  await page.getByRole("link", { name: /check them/i }).click();
  await expect(page).toHaveURL(/\/capture\/check/);
  await expect(menu.getByRole("link", { name: "Marking" })).toHaveAttribute("aria-current", "page");
  await page.getByRole("link", { name: "← Marking" }).click();
  await expect(page).toHaveURL(/\/capture$/);
});

test("by class, by child and by worksheet, each count is where the engine says each answer stands", async ({ page }) => {
  // by class: the test's class, as its papers were made
  await page.goto("/capture?by=class");
  const cls = page.getByRole("row").filter({ has: page.getByRole("link", { name: SECTION, exact: true }) });
  const mine = await counts(sql`ch.section = ${SECTION}`);
  expect(mine).toEqual({ papers: 3, engine: 8, person: 3, waiting: 4 });
  expect(await shown(cls)).toEqual(mine);
  await expect(cls).toContainText("1 of 3 signed off");

  // by child: the class opens as its children
  await cls.getByRole("link", { name: SECTION, exact: true }).click();
  await expect(page).toHaveURL(`/capture?by=child&class=${SECTION}`);
  for (const [name, id] of Object.entries(kids)) {
    const row = page.getByRole("row").filter({ has: page.getByRole("link", { name, exact: true }) });
    expect(await shown(row)).toEqual(await counts(sql`ch.id = ${id}::uuid`));
  }

  // by worksheet: every child who sat it, together
  await page.goto("/capture?by=worksheet");
  const a = page.getByRole("row").filter({ has: page.getByRole("link", { name: "U3 paper A", exact: true }) });
  const sheetA = await counts(sql`t.batch_id = 'U3-A'`);
  expect(sheetA).toEqual({ papers: 2, engine: 6, person: 2, waiting: 2 });
  expect(await shown(a)).toEqual(sheetA);
  await a.getByRole("link", { name: "U3 paper A", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("U3 paper A");
  for (const name of ["Dev", "Esha"]) await expect(page.getByRole("main").getByText(name, { exact: true })).toBeVisible();
});

test("the queue of answers to check sits inside marking with its count, one click away", async ({ page }) => {
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from item_result r join capture c on c.id = r.capture_id
    where c.superseded_by is null and r.status in ('unreadable', 'needs_teacher')`;
  expect(n).toBeGreaterThanOrEqual(3);
  await page.goto("/capture");
  const queue = page.getByRole("region", { name: "Answers to check" });
  await expect(queue.getByTestId("count")).toHaveText(String(n));
  await queue.getByRole("link", { name: /check them/i }).click();
  await expect(page.getByText(`${n} answers left to check`)).toBeVisible();
});

test("a paper shows its score once nothing on it waits", async ({ page }) => {
  await page.goto(`/capture?child=${kids.Dev}`);
  const signed = page.getByRole("row").filter({ hasText: "U3 paper A" });
  // five answers, all settled: four right — one of them judged by a person — and one wrong
  await expect(signed).toContainText("4 / 5 right");
  await expect(signed).toContainText("signed off");
  const open = page.getByRole("row").filter({ hasText: "U3 paper B" });
  await expect(open).not.toContainText("right");
  await expect(open).toContainText("2 need your eyes");
});

test("every marking view fits a phone, with the class's own papers on it", async ({ page }) => {
  const [{ paper }] = await sql<{ paper: string }[]>`select id as paper from sheet_instance where qr_code = 'U3TEST-1'`;
  await page.setViewportSize({ width: 400, height: 860 });
  for (const url of ["/capture?by=class", "/capture?by=child", "/capture?by=worksheet", "/capture?worksheet=U3-A", `/capture?child=${kids.Dev}`, `/capture/${paper}`]) {
    await page.goto(url, { waitUntil: "networkidle" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `${url} must not scroll sideways`).toBeLessThanOrEqual(1);
  }
});
