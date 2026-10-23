/**
 * U51 — The educator's site is held to its rules (goals/uxf-ux-foundation.yaml, docs/ux-rules.md). Nimish, 2026-10-22:
 * "a significant shift to the ui/ux - ensuring there are proper rules/flows/tabular views, no long table, all info
 * displayed is consistent, well formatted, every page has a purpose, a sequence and all pages, flows, views are educator
 * backward".
 *
 * Every page is read as it renders and held to the rules that can be measured there: a table past the row limit, a column
 * of zeros or dashes, a count that differs from the menu's, a page with no main action or no next step, a line under the
 * title past 140 characters. A page that still breaks one is named in `workflows.json` under `ux.frozen` with the rules its code breaks
 * (the list only shrinks: tests/test_ux_rules.py, `engine ratchet`); a page off the list must keep them all. The
 * rules that can be read from the code alone are held by packages/engine/tests/test_ux_rules.py, with no database.
 *
 * A class of the test's own, twelve children, makes the longest table the site draws; it and a paper with an answer
 * waiting are kept (evidence is append-only), as the other specs' are.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { SIGNED_IN } from "../playwright.config";
import { FILTER_FROM_ROWS, PURPOSE_MAX, SEARCH_PX, TABLE_ROW_LIMIT, TOP_BAR_MIN_PX, TOP_BAR_TEXT_PX, groupRows, isEmptyCell, pageOf, visibleColumns } from "../lib/ux-rules";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U51-CLASS";
const NAMES = ["Asha", "Bina", "Chitra", "Dev", "Esha", "Farid", "Gita", "Hari", "Indu", "Jai", "Kiran", "Lata"];
const FROZEN: Record<string, string[]> = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../workflows.json"), "utf8"),
).ux.frozen;
const PHONE = { width: 390, height: 844 };
let kids: Record<string, string>;
let sheet: string;
let answer: string;

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", NAMES);
  const [ws] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template
    where source = 'library' and retired_at is null and skill_set_code = 'ADD.2D2D' and difficulty = 'Medium' order by code limit 1`;
  ({ sheet } = await aReadPaper(sql, {
    qr: "CS51A001",
    child: kids.Asha,
    template: ws.id,
    items: ws.item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  }));
  [{ id: answer }] = await sql<{ id: string }[]>`
    select r.id from item_result r join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id
    where si.qr_code = 'CS51A001' and r.status = 'needs_teacher' limit 1`;
});
test.afterAll(async () => {
  await sql.end();
});

test("the rules are numbers in one place: ten rows, 140 characters", () => {
  expect([TABLE_ROW_LIMIT, PURPOSE_MAX]).toEqual([10, 140]);
});

test("a cell of nothing, a dash or a zero is empty; a column of them is not shown", () => {
  for (const v of [null, undefined, "", " ", "—", "-", "–", 0, "0", "0.0", false]) expect(isEmptyCell(v), String(v)).toBe(true);
  for (const v of [1, "10", "a", "0 of 4", "—x"]) expect(isEmptyCell(v), String(v)).toBe(false);
  type Row = { name: string; late: number; note: string };
  const col = (key: keyof Row, keep = false) => ({ key, label: key, value: (r: Row) => r[key], keep });
  const rows: Row[] = [{ name: "a", late: 0, note: "—" }, { name: "b", late: 0, note: "" }];
  expect(visibleColumns([col("name"), col("late"), col("note")], rows).map((c) => c.key)).toEqual(["name"]);
  expect(visibleColumns([col("name"), col("late", true)], rows).map((c) => c.key)).toEqual(["name", "late"]);
  expect(visibleColumns([col("name"), col("late")], [{ ...rows[0], late: 2 }]).map((c) => c.key)).toEqual(["name", "late"]);
});

test("rows past the limit are paged or grouped, never shown at once", () => {
  const rows = Array.from({ length: 23 }, (_, i) => ({ week: i < 12 ? "W41" : "W40", i }));
  expect(pageOf(rows, 1).rows).toHaveLength(TABLE_ROW_LIMIT);
  expect(pageOf(rows, 3)).toMatchObject({ page: 3, pages: 3 });
  expect(pageOf(rows, 3).rows).toHaveLength(3);
  expect(pageOf(rows, 99).page).toBe(3); // a page past the end is the last
  expect(pageOf([], 1)).toMatchObject({ page: 1, pages: 1 });
  expect(groupRows(rows, (r) => r.week).map((g) => [g.name, g.rows.length])).toEqual([["W41", 12], ["W40", 11]]);
});

async function open(page: Page, url: string) {
  await page.goto(url);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText("Loading…");
}

/** What a rendered page breaks, by rule name (the names of workflows.json `ux.frozen`). */
async function breaks(page: Page): Promise<string[]> {
  return page.evaluate(
    ({ limit, max, filterFrom }) => {
      const out = new Set<string>();
      // a table of six rows or more has the one filter row above it (rule 9); a state is never colour alone (rule 10)
      if ([...document.querySelectorAll("main table")].some((t) => t.querySelectorAll("tbody tr:not(.under)").length >= filterFrom) && !document.querySelector("main [data-filterbar]")) out.add("no-filter");
      if ([...document.querySelectorAll("main [data-status]")].some((c) => !c.querySelector("svg") || !(c.textContent ?? "").trim())) out.add("no-icon");
      const empty = (s: string) => /^\s*([-–—]|0+([.,]0+)?)?\s*$/.test(s);
      for (const t of document.querySelectorAll("main table")) {
        const rows = [...t.querySelectorAll("tbody tr")];
        if (rows.length > limit) out.add("long-table");
        // a paged table keeps its columns the same on every page: a column with nothing on this page has its words on another
        const paged = !!t.closest("div")?.parentElement?.querySelector("nav[aria-label$=' pages']");
        const width = paged ? 0 : Math.max(0, ...rows.map((r) => r.children.length));
        for (let c = 0; c < width; c++) {
          const cells = rows.map((r) => r.children[c]).filter(Boolean);
          const head = t.querySelectorAll("thead th")[c];
          if (cells.length > 1 && head && head.textContent?.trim() && cells.every((x) => empty(x.textContent ?? ""))) out.add("empty-column");
        }
      }
      const seen = new Map<string, Set<string>>();
      for (const el of document.querySelectorAll("[data-count]")) {
        const k = el.getAttribute("data-count")!;
        seen.set(k, (seen.get(k) ?? new Set()).add((el.textContent ?? "").trim()));
      }
      if ([...seen.values()].some((v) => v.size > 1)) out.add("count");
      if (!document.querySelector("[data-ux=action]") || !document.querySelector("[data-ux=next]")) out.add("shell");
      const purpose = document.querySelector("main header p");
      if (purpose && (purpose.textContent ?? "").length > max) out.add("line");
      return [...out];
    },
    { limit: TABLE_ROW_LIMIT, max: PURPOSE_MAX, filterFrom: FILTER_FROM_ROWS },
  );
}

const ROUTES = (): [string, string][] => [
  ["/today", "/today"],
  ["/", "/"],
  ["/library", "/library"],
  ["/worksheets", "/worksheets"],
  ["/worksheets/taxonomy", "/worksheets/taxonomy"],
  ["/worksheets/[qr]", "/worksheets/CS51A001"],
  ["/papers", "/papers"],
  ["/papers/make", "/papers/make"],
  ["/make", "/make"],
  ["/make/[section]", `/make/${SECTION}`],
  ["/make/[section]/week", `/make/${SECTION}/week`],
  ["/capture", "/capture"],
  ["/capture/[id]", `/capture/${sheet}`],
  ["/capture/check", `/capture/check?id=${answer}`],
  ["/growth", "/growth"],
  ["/growth/class/[section]", `/growth/class/${SECTION}`],
  ["/growth/[id]", `/growth/${kids.Asha}`],
  ["/growth/reports", "/growth/reports"],
  ["/asks", "/asks"],
  ["/home", "/home"],
  ["/workflows", "/workflows"],
];

test("every page keeps the rules, or is named as still breaking them, and only those", async ({ browser }) => {
  test.setTimeout(300_000);
  const page = await (await browser.newContext({ storageState: SIGNED_IN })).newPage();
  const wrong: string[] = [];
  const measured: string[] = [];
  for (const [route, url] of ROUTES()) {
    await open(page, url);
    const found = await breaks(page);
    // A page still on the list is built by hand and shows whatever the rows give it: measured, not held. A page off it
    // is on the blocks and keeps every rule.
    if (FROZEN[route]) measured.push(`${route}: ${found.join(", ") || "-"}`);
    else if (found.length) wrong.push(`${route}: ${found.join(", ")}`);
  }
  test.info().annotations.push({ type: "still breaking, by hand", description: measured.join("\n") });
  expect(wrong, "a page off workflows.json ux.frozen breaks a rule").toEqual([]);
  await page.context().close();
});

test("Check answers is built on the blocks: one main action, its next step, one count", async ({ browser }) => {
  const page = await (await browser.newContext({ storageState: SIGNED_IN })).newPage();
  await open(page, `/capture/check?id=${answer}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check the answers");
  expect(await breaks(page)).toEqual([]);
  expect(FROZEN["/capture/check"]).toBeUndefined();
  // the progress line is all that sits above the card; the decision (Right/Wrong/Blank, or "Yes, the child wrote…")
  // is in the answer box, beside the sentence it answers (Nimish, 23 Oct 2026)
  await expect(page.locator("[data-ux=action] button")).toHaveCount(0);
  await expect(page.locator("form button[type=submit]").first()).toBeVisible();
  await expect(page.locator("[data-ux=next]")).toHaveAttribute("href", /\/(capture\/check\?from=|growth)/);
  const waiting = await page.locator('[data-count="answers to check"]').textContent();
  expect(Number(waiting?.replace(/\D/g, ""))).toBeGreaterThan(0);
  await page.context().close();
});

test("on a phone the main action of Check answers is a thumb's size", async ({ browser }) => {
  const page = await (await browser.newContext({ storageState: SIGNED_IN, viewport: PHONE })).newPage();
  await open(page, `/capture/check?id=${answer}`);
  for (const b of await page.locator("[data-ux=action] button, [data-ux=action] a, [data-ux=next]").all()) {
    expect((await b.boundingBox())!.height, await b.textContent() ?? "").toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.context().close();
});


const DESKTOP = { width: 1440, height: 900 };

test("the top bar: Class and Subject are full-size controls, the student search is a compact field", async ({ browser }) => {
  const page = await (await browser.newContext({ storageState: SIGNED_IN, viewport: DESKTOP })).newPage();
  for (const url of ["/today", "/papers", "/growth", "/"]) {
    await open(page, url);
    const bar = page.getByRole("search", { name: "Subject, class and search" });
    for (const name of ["Subject", "Class"]) {
      const box = (await bar.getByLabel(name, { exact: true }).boundingBox())!;
      expect(box.height, `${url}: ${name} height`).toBeGreaterThanOrEqual(TOP_BAR_MIN_PX);
      expect(box.width, `${url}: ${name} is not squeezed`).toBeGreaterThanOrEqual(80);
      const size = await bar.getByLabel(name, { exact: true }).evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
      expect(size, `${url}: ${name} text`).toBeGreaterThanOrEqual(TOP_BAR_TEXT_PX);
    }
    const search = bar.getByRole("searchbox");
    const box = (await search.boundingBox())!;
    expect(box.height).toBeGreaterThanOrEqual(TOP_BAR_MIN_PX);
    expect(Math.round(box.width), `${url}: the search is a field, about ${SEARCH_PX} px`).toBeLessThanOrEqual(SEARCH_PX + 20);
    expect(Math.round(box.width)).toBeGreaterThanOrEqual(SEARCH_PX - 20);
    await search.focus();
    await expect.poll(async () => Math.round((await search.boundingBox())!.width)).toBeGreaterThan(SEARCH_PX + 40);
  }
  await page.context().close();
});

test("Assessments is a table of aligned columns with the one filter row, and a status is an icon, a word and a colour", async ({ browser }) => {
  const page = await (await browser.newContext({ storageState: SIGNED_IN, viewport: DESKTOP })).newPage();
  await open(page, "/papers");
  expect(FROZEN["/papers"]).toBeUndefined();
  expect(await breaks(page)).toEqual([]);
  const table = page.getByRole("table", { name: "Assessments" });
  const heads = (await table.locator("thead th").allTextContents()).map((h) => h.trim());
  for (const h of ["Class", "Assessment", "Kind", "Stage", "Papers in", "Status"]) expect(heads, "columns").toContain(h);
  // text left, numbers right, a state in the middle: heading and cells together
  const align = async (name: string) => {
    const i = heads.indexOf(name);
    return table.locator(`tbody tr[data-assessment] td:nth-child(${i + 1})`).first().evaluate((el) => getComputedStyle(el).textAlign);
  };
  expect(await align("Assessment")).toBe("left");
  expect(await align("Papers in")).toBe("right");
  expect(await align("Status")).toBe("center");
  // every status carries an icon and a word, and is one of the three colours
  const chips = table.locator("[data-status]");
  expect(await chips.count()).toBeGreaterThan(0);
  for (const c of await chips.all()) {
    await expect(c.locator("svg")).toHaveCount(1);
    expect((await c.textContent())!.trim().length).toBeGreaterThan(2);
    expect(["ok", "wait", "act", "quiet"]).toContain(await c.getAttribute("data-tone"));
  }
  // the filter row is in the same place, and a filter shows itself and clears in one click
  const filters = page.locator("[data-filterbar]");
  await expect(filters).toBeVisible();
  await filters.locator('select[name="kind"]').selectOption("assessment");
  await expect(page).toHaveURL(/kind=assessment/);
  await expect(page.locator("[data-active-filters]")).toContainText("Kind: Class assessment");
  await page.locator("[data-active-filters]").getByRole("link", { name: "Clear" }).click();
  await expect(page).not.toHaveURL(/kind=/);
  await expect(page.locator("[data-active-filters]")).toHaveCount(0);
  await page.context().close();
});
