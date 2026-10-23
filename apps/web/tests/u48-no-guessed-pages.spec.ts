/**
 * U48 — a page whose code cannot be read is never guessed onto a child (goals/ux9a-no-guessed-pages.yaml). Nimish,
 * 2026-10-22, on PR #252's question (such a page, inside a child's copy short of a page, was read as that copy's next
 * page): "yes, stop guessing." It stays unread, is listed on Marking by its page number, and is read only once the
 * educator has said whose it is, in one tap.
 *
 * The file is the engine's own print of a library worksheet for two children of a class of the test's own, each copy
 * with its child's code, the first child's first page with its code covered. It is put in on Marking as an educator
 * puts one in. Reading the boxes needs Amazon's reader, which a test machine has not got, so there the run stops at it;
 * what the sorting came to is then written onto that same run as the engine writes it (`inbox.read`, as u44 does).
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U48-G3";
const WORKSHEET = "R22-H03";
const FILE = `U48 scan ${Date.now()}.pdf`;
const dir = path.join(__dirname, "..", "test-results", "u48");
const scan = path.join(dir, FILE);
let pages = 0;
let kids: Record<string, string> = {};

test.beforeAll(async () => {
  kids = await aClass(sql, CLASS, "G3", ["Ana", "Bo"]);
  const res = await fetch(`http://127.0.0.1:${ENGINE_PORT}/worksheet/${WORKSHEET}/for.pdf`, {
    method: "POST",
    headers: { "X-Engine-Key": process.env.E2E_ENGINE_KEY!, "content-type": "application/json" },
    body: JSON.stringify({ children: [kids.Ana, kids.Bo], week: "2026-W43", by: "e2e@cornerstone.test" }),
  });
  expect(res.status, await res.clone().text()).toBe(200);
  mkdirSync(dir, { recursive: true });
  const printed = path.join(dir, "printed.pdf");
  writeFileSync(printed, Buffer.from(await res.arrayBuffer()));
  // the printed copies as a scanner gives them, the first page's code covered: its corner, and the code in words
  const python = path.resolve(__dirname, "../../../packages/engine/.venv/bin/python");
  pages = Number(
    execFileSync(python, [
      "-c",
      [
        "import sys, pymupdf",
        "d = pymupdf.open(sys.argv[1]); p = d[0]; r = p.rect",
        "p.draw_rect(pymupdf.Rect(r.width * 0.5, 0, r.width, r.height * 0.22), color=(1, 1, 1), fill=(1, 1, 1))",
        "[p.draw_rect(h + (-4, -4, 80, 4), color=(1, 1, 1), fill=(1, 1, 1)) for h in p.search_for('CS')]",
        "d.save(sys.argv[2]); print(len(d))",
      ].join("\n"),
      printed,
      scan,
    ]).toString(),
  );
});
test.afterAll(async () => {
  await sql`delete from flow_run where flow = 'read-scan' and trigger like ${`%${FILE}`}`;
  await sql.end();
});

test("a page whose code cannot be read is listed by its number, read as no child's, and given to one in one tap", async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto("/capture");
  const panel = page.getByRole("region", { name: "Read a scan" });
  await panel.getByLabel("Choose scans").setInputFiles([scan]);
  const table = panel.getByRole("table", { name: "Scans read last" });
  const run = table.getByRole("row").filter({ hasText: FILE }).first();
  await expect(run).toContainText(`${pages} pages`, { timeout: 60_000 });
  await expect(run).not.toContainText("reading now", { timeout: 120_000 });
  const [f] = await sql<{ id: string }[]>`select id from flow_run where flow = 'read-scan' and trigger like ${`%${FILE}`}`;

  // what the sorting came to, as the engine writes it: Ana's copy without its first page, which is nobody's
  const half = pages / 2;
  const span = (from: number, n: number) => Array.from({ length: n }, (_, i) => from + i);
  const copies = [
    { copy: 1, pages: [1], code: "?", child_id: null, answers: 0, by_code: false, skipped: true, why: "no code could be read on the page", no_code: [1] },
    { copy: 2, pages: span(2, half - 1), code: WORKSHEET, child_id: kids.Ana, answers: 0, by_code: true, no_code: [], given: [],
      missing: [1], lacks: [`page 1 of ${half} is not in this file: scan it and send it to be read`] },
    { copy: 3, pages: span(half + 1, half), code: WORKSHEET, child_id: kids.Bo, answers: 0, by_code: true, no_code: [], given: [],
      missing: [], lacks: [] },
  ];
  await sql`update flow_run set status = 'ok', error = null, result = result || ${sql.json({ copies })} where id = ${f.id}`;
  await page.reload();

  // listed by its number, its picture beside it, not read: one button for the child a page short, the rest folded
  const waiting = table.getByRole("list", { name: `Pages of ${FILE} waiting for their child` }).getByRole("listitem");
  await expect(waiting).toHaveCount(1);
  await expect(waiting).toContainText("Page 1: no code could be read on it, so it is not read until you say whose it is.");
  const picture = await page.request.get(`/api/scan-run/${f.id}/1`);
  expect(picture.status()).toBe(200);
  expect(picture.headers()["content-type"]).toBe("image/jpeg");
  const whose = waiting.getByRole("form", { name: "Whose is page 1?" });
  await expect(whose.getByRole("button", { name: `${CLASS} · roll 2` })).toBeHidden();
  await expect(table, "a roll number, never a name").not.toContainText(/Ana|Bo\b/);

  await whose.getByRole("button", { name: `${CLASS} · roll 1 (a page short)` }).click();
  await expect(page).toHaveURL(/read=given/);
  const [{ given }] = await sql<{ given: { page: number; child_id: string; by: string }[] }[]>`
    select result -> 'given' as given from flow_run where id = ${f.id}`;
  expect(given.map((g) => [g.page, g.child_id, g.by])).toEqual([[1, kids.Ana, "e2e@cornerstone.test"]]);
  // the file is read again, the page as Ana's; it no longer waits, and says whose it was given as
  await expect(table).toContainText(`Page 1 given to ${CLASS} · roll 1`);
  await expect(table.getByRole("list", { name: `Pages of ${FILE} waiting for their child` })).toHaveCount(0);
});

test("the engine refuses a page given to a child whose paper is not in the file, in words", async ({ request }) => {
  // a file's run as the engine writes one: Ana's copy read by its code, page 1 nobody's
  const copies = [
    { copy: 1, pages: [1], code: "?", child_id: null, answers: 0, skipped: true, why: "no code could be read on the page", no_code: [1] },
    { copy: 2, pages: [2], code: WORKSHEET, child_id: kids.Ana, answers: 0, by_code: true, no_code: [], missing: [1] },
  ];
  const [t] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  const [{ id: run }] = await sql<{ id: string }[]>`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, result)
    values (${t.id}, 'read-scan', ${`e2e@cornerstone.test: ${FILE}`}, 'ok', now(), ${sql.json({ pages: 2, copies })}) returning id`;
  const { Cy: other } = await aClass(sql, `${CLASS}B`, "G3", ["Cy"]);
  const res = await request.post(`http://127.0.0.1:${ENGINE_PORT}/read/run/${run}/page`, {
    headers: { "X-Engine-Key": process.env.E2E_ENGINE_KEY! },
    data: { page: 1, child_id: other, by: "e2e@cornerstone.test" },
  });
  expect(res.status()).toBe(409);
  expect((await res.json()).detail).toBe("no paper of that child is in this file, so the page cannot be read as theirs");
});
