/**
 * U10 — tables that read straight (goals/u10-tables-read-straight.yaml).
 *
 * Nimish, 2026-09-30, over the Marking page's reader tables: "The column names are not well formatted and
 * center-aligned … The table alignment, like the column names and the table alignment, is distorted across all the
 * places." And: "It simply shows just one table, which can have a toggle around confidence levels, the date, etc.
 * There's just one table which very clearly shows how the engine is improving or not".
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
const SECTION = "U10-TEST";

/** Two days of checked answers, made once and kept: on 1 August the reader read two answers and a person put one right
 *  (half right); on 2 August it read two and both stood (all right) — so 2 August is 50 points up on 1 August. */
async function twoDays() {
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION}`;
  const kid =
    had?.id ??
    (await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${tenant}, '1', ${SECTION}, 'G2') returning id`)[0].id;
  // a child on the roll has a name: the pages read names through pii.read_child, and a nameless child is on none
  await sql`insert into pii.child (tenant_id, child_id, first_name) select ${tenant}, ${kid}, 'Ira'
            where not exists (select 1 from pii.child where child_id = ${kid})`;
  const [papers] = await sql`select 1 from sheet_instance where child_id = ${kid}`;
  if (papers) return;
  for (const [day, readings] of [["2026-08-01", [["35", null], ["35", "34"]]], ["2026-08-02", [["35", null], ["35", null]]]] as const) {
    const [{ id: tpl }] = await sql<{ id: string }[]>`
      insert into sheet_template (tenant_id, band, week, source, child_id, key) values (${tenant}, 'G2', 'U10-W', 'legacy', ${kid}, '{}')
      returning id`;
    const [{ id: si }] = await sql<{ id: string }[]>`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status, section, week)
      values (${tenant}, ${`U10-${day}`}, ${tpl}, ${kid}, 'returned', ${SECTION}, 'U10-W') returning id`;
    const [{ id: cap }] = await sql<{ id: string }[]>`
      insert into capture (tenant_id, path, pages, sheet_instance_id, status, created_at)
      values (${tenant}, 'u10', 1, ${si}, 'processed', ${`${day} 10:00+05:30`}) returning id`;
    for (const [n, [read, typed]] of readings.entries()) {
      // a test's own question, entered as an earlier paper's (`legacy`): the bank's checks are for the questions it
      // generates, and four tests' "generated" rows broke `engine audit` on the copy (2026-10-01)
      const [{ id: item }] = await sql<{ id: string }[]>`
        insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses, source)
        values (${tenant}, ${`u10/${day}/${n}`}, 'u10', 'R24', '{NUM.OPS.02}', 'Procedural', 'missing_number',
                ${sql.json({ op: "-", a: 62, b: 27 })}, ${sql.json([{ rid: "a", answer: 35 }])}, 'legacy') returning id`;
      const [{ id: result }] = await sql<{ id: string }[]>`
        insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, state)
        values (${tenant}, ${cap}, ${item}, 'a', ${JSON.stringify({ child_answer: read })}, ${typed === "34" ? "wrong" : "correct"}, 'confirmed')
        returning id`;
      if (typed) {
        await sql`insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, misconception_codes, by)
                  values (${tenant}, ${kid}, ${cap}, ${result}, ${read}, ${typed}, '{}', 'e2e')`;
      }
    }
  }
}

test.beforeAll(twoDays);
test.afterAll(async () => sql.end());

/** Each heading whose alignment is not its column's: a heading on the left over numbers in the middle reads as
 *  another column. Compared as the browser draws them, for every table on the page with a body row. */
async function offColumn(page: Page): Promise<string[]> {
  await expect(page.locator("table.grid tbody tr").first()).toBeVisible();
  return page.locator("table.grid").evaluateAll((tables) => {
    const side = (el: Element) => ({ start: "left", end: "right" })[getComputedStyle(el).textAlign] ?? getComputedStyle(el).textAlign;
    return tables.flatMap((t, n) => {
      const heads = [...t.querySelectorAll("thead tr:last-child th")];
      // a heading that spans the heading rows (a class grid's "Child") heads the first cells: the last row heads the rest
      const cells = [...(t.querySelector("tbody tr")?.querySelectorAll("td") ?? [])].slice(-heads.length);
      if (!cells.length || heads.length > cells.length) return [];
      return heads.flatMap((h, i) =>
        side(h) === side(cells[i]) ? [] : [`${t.getAttribute("aria-label") ?? `table ${n + 1}`} · "${h.textContent?.trim()}": heading ${side(h)}, cells ${side(cells[i])}`],
      );
    });
  });
}

test("every heading sits over its own column, on every page with a table", async ({ page }) => {
  const [grid] = await sql<{ section: string }[]>`
    select c.section from child_skill_state s join child c on c.id = s.child_id where c.active and s.n_events > 0 limit 1`;
  for (const path of ["/", "/papers", "/capture", "/growth", "/make", "/library", "/worksheets", `/growth/class/${grid.section}`]) {
    await page.goto(path);
    expect(await offColumn(page), path).toEqual([]);
  }
  // the reader's table, in each of its views
  await page.goto("/capture");
  const panel = page.getByRole("region", { name: "How the reader is doing" });
  for (const view of ["By kind of question", "By how sure it was"]) {
    await panel.getByRole("button", { name: view }).click();
    expect(await offColumn(page), view).toEqual([]);
  }
});

test("how the reader is doing is one table, by day first, by kind or by how sure at a click", async ({ page }) => {
  await page.goto("/capture");
  const panel = page.getByRole("region", { name: "How the reader is doing" });
  const show = panel.getByRole("group", { name: "Show the reader" });
  const table = panel.getByRole("table", { name: "How the reader is doing" });
  await expect(panel.getByRole("table")).toHaveCount(1);
  await expect(show.getByRole("button", { name: "By day" })).toHaveAttribute("aria-pressed", "true");
  await expect(table.locator("thead th")).toHaveText(["Papers read on", "Answers checked", "Reader right", "Against the day before", "Gave up"]);

  await show.getByRole("button", { name: "By kind of question" }).click();
  await expect(show.getByRole("button", { name: "By kind of question" })).toHaveAttribute("aria-pressed", "true");
  await expect(table.locator("thead th").first()).toHaveText("Kind of question");
  // every kind in words: never a code like word_2step
  for (const kind of await table.locator("tbody td:first-child").allInnerTexts()) expect(kind).not.toMatch(/_/);

  await show.getByRole("button", { name: "By how sure it was" }).click();
  await expect(table.locator("thead th").first()).toHaveText("Reader was this sure");
  await expect(panel.getByRole("table")).toHaveCount(1);
});

test("each day says how far the reader moved against the day before, and the words say first against latest", async ({ page }) => {
  const [{ n }] = await sql<{ n: number }[]>`select count(distinct read_on)::int as n from answer_checked`;
  await page.goto("/capture");
  const panel = page.getByRole("region", { name: "How the reader is doing" });
  const rows = panel.getByRole("table", { name: "How the reader is doing" }).locator("tbody tr");
  await expect(rows).toHaveCount(n);
  // newest first: each day's move is its share right less the day before's, as the table itself shows them
  const cells = await rows.evaluateAll((trs) => trs.map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent!.trim())));
  const right = cells.map((c) => (c[2] === "—" ? null : Number(c[2].replace("%", ""))));
  for (const [i, c] of cells.entries()) {
    const before = right[i + 1];
    const expected = right[i] === null || before === undefined || before === null ? "—"
      : right[i] === before ? "no change" : `${right[i]! > before ? "▲" : "▼"} ${Math.abs(right[i]! - before)} points`;
    expect(c[3], `${c[0]}`).toBe(expected);
  }
  // the test's own two days: all right on 2 August, half on 1 August — 50 points up
  const aug2 = cells.find((c) => c[0] === "02-Aug-2026");
  expect(aug2?.[2]).toBe("100%");
  if (cells.findIndex((c) => c[0] === "01-Aug-2026") === cells.indexOf(aug2!) + 1) expect(aug2?.[3]).toBe("▲ 50 points");
  const read = cells.filter((c) => c[2] !== "—");
  if (read.length > 1) {
    await expect(panel).toContainText(`it was right on ${read[read.length - 1][2]}; on the latest`);
    await expect(panel).toContainText(`, ${read[0][2]}.`);
  }
});
