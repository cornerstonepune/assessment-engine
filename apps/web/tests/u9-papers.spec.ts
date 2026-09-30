/**
 * U9 — Papers (goals/u9-papers.yaml).
 *
 * Nimish, 2026-09-30: "I really don't think marking and marking papers as two different types are essential. We can
 * merge them into one" and "one list of papers with the right filtration and all, and a good view". One menu item,
 * one table of every paper: what it is, whose, its kind and week, where it stands, what waits for a person, filtered
 * by class, child, kind, week and stage; a row opens the paper where its work is.
 *
 * The class is the test's own, two Grade 2 children, with four papers made once and kept:
 * - a class practice proposed and not yet approved (made);
 * - a home assessment approved for print (printed);
 * - an earlier paper read, one answer still waiting for a person (scanned);
 * - a class assessment read and signed off, one of two right (signed off).
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U9-TEST";
const WEEK = "U9-W";

type Paper = { id: string; qr: string };
const papers: Record<"made" | "printed" | "scanned" | "signed", Paper> = {} as never;
let kids: Record<string, string> = {};

async function child(tenant: string, roll: string, name: string) {
  const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = ${roll}`;
  if (had) return had.id;
  const [{ id }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant}, ${roll}, ${SECTION}, 'G2') returning id`;
  await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant}, ${id}, ${name})`;
  return id;
}

async function paper(
  tenant: string,
  qr: string,
  kid: string,
  t: { source: string; set?: string; level?: string; key?: object; drawn?: string[] },
  i: { kind: string | null; status: string; approved?: boolean },
): Promise<Paper> {
  const [had] = await sql<Paper[]>`select id, qr_code as qr from sheet_instance where qr_code = ${qr}`;
  if (had) return had;
  const [{ id: tpl }] = await sql<{ id: string }[]>`
    insert into sheet_template (tenant_id, band, week, source, skill_set_code, difficulty, child_id, key, item_ids)
    values (${tenant}, 'G2', ${WEEK}, ${t.source}, ${t.set ?? null}, ${t.level ?? null}, ${kid}, ${sql.json((t.key ?? {}) as never)},
            ${t.drawn ?? null}::uuid[])
    returning id`;
  const [p] = await sql<Paper[]>`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status, kind, week, section,
                                approved_by, approved_at)
    values (${tenant}, ${qr}, ${tpl}, ${kid}, ${i.status}, ${i.kind}, ${WEEK}, ${SECTION},
            ${i.approved ? "e2e" : null}, ${i.approved ? sql`now()` : null})
    returning id, qr_code as qr`;
  return p;
}

async function read(tenant: string, p: Paper, answers: [status: string, state: string][]) {
  const [had] = await sql`select 1 from capture where sheet_instance_id = ${p.id}`;
  if (had) return;
  const [{ id: cap }] = await sql<{ id: string }[]>`
    insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (${tenant}, 'u9', 1, ${p.id}, 'processed')
    returning id`;
  for (const [n, [status, state]] of answers.entries()) {
    const [{ id: item }] = await sql<{ id: string }[]>`
      insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses)
      values (${tenant}, ${`u9/${p.qr}/${n}`}, 'u9', 'R24', '{NUM.OPS.02}', 'Procedural', 'column',
              ${sql.json({ op: "-", a: 62, b: 27 })}, ${sql.json([{ rid: "a", answer: 35 }])})
      returning id`;
    await sql`insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, state)
              values (${tenant}, ${cap}, ${item}, 'a', '{"child_answer": "35"}', ${status}, ${state})`;
  }
}

test.beforeAll(async () => {
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  kids = { Asha: await child(tenant, "1", "Asha"), Bina: await child(tenant, "2", "Bina") };
  papers.made = await paper(tenant, "U9-MADE", kids.Bina, { source: "generated", set: "ADD.2D2D", level: "Easy" }, { kind: "practice", status: "new" });
  // a home paper as the engine makes it (focus_paper.make): its questions, and no skill set of its own
  const drawn = await sql<{ id: string }[]>`
    select id from item where status = 'active' and skill_set_code = 'SUB.2D2D' and difficulty = 'Medium' order by item_key limit 3`;
  papers.printed = await paper(tenant, "CSE9A001", kids.Asha, { source: "focus", drawn: drawn.map((d) => d.id) }, { kind: "focus", status: "printed", approved: true });
  papers.scanned = await paper(tenant, "U9-OLD-A", kids.Asha, { source: "legacy", key: { title: "U9 September paper", date: "2026-09-21" } }, { kind: null, status: "returned" });
  papers.signed = await paper(tenant, "U9-ASSESS", kids.Bina, { source: "generated", set: "SUB.2D2D", level: "Hard" }, { kind: "assessment", status: "returned" });
  await read(tenant, papers.scanned, [["needs_teacher", "candidate"], ["correct", "candidate"]]);
  await read(tenant, papers.signed, [["correct", "confirmed"], ["wrong", "confirmed"]]);
});
test.afterAll(async () => sql.end());

const row = (page: Page, p: Paper) => page.locator(`tbody tr[data-paper="${p.id}"]`);
const setName = async (code: string) =>
  (await sql<{ name: string }[]>`select name from skill_set where code = ${code} limit 1`)[0].name;

test("every paper is one row, what it is, whose, and where it stands, filtered by class, kind and stage", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Papers");
  const table = page.getByRole("table", { name: "Every paper" });
  await expect(table.locator("thead th")).toHaveText([/Paper/, /Kind/, /Class/, /Child/, /Week/, /Stage/, /Waiting/, /Score/]);
  await expect(table.locator("tbody tr")).toHaveCount(4);

  const cells = (p: Paper) => row(page, p).locator("td");
  await expect(cells(papers.made)).toHaveText([`${await setName("ADD.2D2D")} · Easy`, "Class practice", SECTION, "Bina", WEEK, "made", "—", "—"]);
  await expect(cells(papers.printed)).toHaveText([`${await setName("SUB.2D2D")} · Medium`, "Home assessment", SECTION, "Asha", WEEK, "printed", "—", "—"]);
  await expect(cells(papers.scanned)).toHaveText(["U9 September paper", "Earlier paper", SECTION, "Asha", WEEK, "scanned", "1", "—"]);
  await expect(cells(papers.signed)).toHaveText([`${await setName("SUB.2D2D")} · Hard`, "Class assessment", SECTION, "Bina", WEEK, "signed off", "—", "1 of 2"]);
  // in the school's words: no rung, skill or mistake code reaches a teacher
  await expect(table).not.toContainText(/\b(R\d{1,2}|X[12]|M_[A-Z0-9_]+|[A-Z]{3}\.[A-Z0-9]+\.[A-Z0-9]+)\b/);

  // each stage is counted, and a count is the filter
  const stages = page.getByRole("navigation", { name: "Papers by stage" });
  await expect(stages.getByRole("link", { name: /scanned/ })).toContainText("1");
  await stages.getByRole("link", { name: /scanned/ }).click();
  await expect(page).toHaveURL(/stage=scanned/);
  await expect(page).toHaveURL(new RegExp(`class=${SECTION}`));
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(row(page, papers.scanned)).toBeVisible();

  // the filters are a form any of them can narrow
  await page.goto(`/papers?class=${SECTION}`);
  await page.getByLabel("Kind").selectOption({ label: "Home assessment" });
  await page.getByRole("button", { name: "Show" }).click();
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(row(page, papers.printed)).toBeVisible();
  await page.getByLabel("Child").selectOption({ label: `Bina · ${SECTION} roll 2` });
  await page.getByLabel("Kind").selectOption({ label: "Any kind" });
  await page.getByRole("button", { name: "Show" }).click();
  await expect(table.locator("tbody tr")).toHaveCount(2);
});

test("one Papers in the menu for marking and making, and a row opens the paper where its work is", async ({ page }) => {
  await page.goto("/papers");
  const menu = page.getByRole("navigation", { name: "Sections" });
  await expect(menu.getByRole("link", { name: "Papers" })).toHaveAttribute("aria-current", "page");
  await expect(menu.getByRole("link", { name: "Marking" })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Make papers" })).toHaveCount(0);
  // making, reading a scan and the queue of answers to check are all here
  await expect(page.getByRole("link", { name: "Make a paper" })).toHaveAttribute("href", "/make");
  await expect(page.getByRole("region", { name: "Read a scan" })).toBeVisible();
  await expect(page.getByRole("link", { name: /answers? to check/ })).toHaveAttribute("href", "/capture/check");
  // the pages it merged are still Papers
  for (const path of ["/capture", "/make"]) {
    await page.goto(path);
    await expect(menu.getByRole("link", { name: "Papers" })).toHaveAttribute("aria-current", "page");
  }

  // a scanned paper opens to check its answers; one not yet scanned opens as printed; a click anywhere on the row
  await page.goto(`/papers?class=${SECTION}`);
  const click = async (p: Paper) => {
    // the page streams in behind its skeleton: the row first, on screen, then where it sits
    const cell = row(page, p).locator("td").nth(1);
    await expect(cell).toBeVisible();
    await cell.scrollIntoViewIfNeeded();
    const box = (await cell.boundingBox())!;
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  };
  await click(papers.scanned);
  await expect(page).toHaveURL(`/capture/${papers.scanned.id}`);
  await page.goto(`/papers?class=${SECTION}`);
  await click(papers.printed);
  await expect(page).toHaveURL(`/worksheets/${papers.printed.qr}`);
});
