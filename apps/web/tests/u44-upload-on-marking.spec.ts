/**
 * U44 — a scan put in on Marking (goals/n8-upload-on-marking.yaml, ADR 0092). Nimish, 2026-10-21: "Teachers can directly
 * just put in the assessments, like the PDF copy or scanned copy of the assessments, there. Then the analysis can happen,
 * and there it says we have a proper understanding of how many questions have been evaluated, how many questions need
 * validation from the teacher."
 *
 * The file is the test seed's own printed paper: a library worksheet printed by the engine for two children of a class
 * of the test's own, each copy with its child's code, and a page after them on which no code can be read. It is chosen
 * on the page as an educator chooses one, beside a file that is not a scan; the browser sends each straight to the
 * engine, which takes it into its inbox and starts the run. Reading the boxes needs Amazon's reader, which a test machine
 * has not got, so there the run stops at it, and says so. What the reading came to is then written onto that same run
 * as the reader writes it (`inbox.read`, as u41 does), its copies read through `aReadPaper`, and the page says what was
 * found and how the answers stand, counted as the engine counts them (`answer_standing`).
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";
import { aClass, aReadPaper } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U44-G3";
const WORKSHEET = "R22-H03";
const FILE = `U44 scan ${Date.now()}.pdf`;
const dir = path.join(__dirname, "..", "test-results", "u44");
const scan = path.join(dir, FILE);
const notAScan = path.join(dir, "marks.txt");
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
  writeFileSync(notAScan, "roll,marks\n1,9\n");
  // the printed copies as a scanner gives them, and one page more, blank: no code on it to read
  const python = path.resolve(__dirname, "../../../packages/engine/.venv/bin/python");
  pages = Number(
    execFileSync(python, [
      "-c",
      "import sys, pymupdf\nd = pymupdf.open(sys.argv[1])\nd.new_page()\nd.save(sys.argv[2])\nprint(len(d))",
      printed,
      scan,
    ]).toString(),
  );
});
test.afterAll(async () => {
  await sql`delete from flow_run where flow = 'read-scan' and trigger like ${`%${FILE}`}`;
  await sql.end();
});

test("a scan put in on Marking is read, and its run says what was found and what waits", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("/capture");
  const panel = page.getByRole("region", { name: "Read a scan" });
  await panel.getByLabel("Choose scans").setInputFiles([scan, notAScan]);

  // each file's own line: how much has gone, and what the engine said; the one it refuses does not stop the other
  const sent = panel.getByRole("list", { name: "Scans sent" }).getByRole("listitem");
  await expect(sent.filter({ hasText: FILE })).toContainText(`${pages} pages found; reading them now`, { timeout: 60_000 });
  const bar = panel.getByRole("progressbar", { name: `Sending ${FILE}` });
  expect(await bar.getAttribute("value")).toBe(await bar.getAttribute("max"));
  await expect(sent.filter({ hasText: "marks.txt" })).toContainText(
    "the engine would not take it: marks.txt is not a PDF or a photo (JPG, PNG or HEIC)",
  );

  // the file's run, refreshed by the page while it is read: its pages from the start
  const table = panel.getByRole("table", { name: "Scans read last" });
  const run = table.getByRole("row").filter({ hasText: FILE }).first();
  await expect(run).toContainText(`${pages} pages`);
  const [f] = await sql<{ id: string; trigger: string; pages: number }[]>`
    select id, trigger, (result ->> 'pages')::int as pages from flow_run where flow = 'read-scan' and trigger like ${`%${FILE}`}`;
  expect(f).toMatchObject({ trigger: `e2e@cornerstone.test: ${FILE}`, pages });
  await expect(run).not.toContainText("reading now", { timeout: 120_000 });

  // what the reading came to, as the reader writes it: each child's copy read by its code, the blank page by its number
  const [t] = await sql<{ id: string; items: string[] }[]>`select id, item_ids as items from sheet_template where code = ${WORKSHEET}`;
  const qr = async (child: string) =>
    (await sql<{ qr: string }[]>`select qr_code as qr from sheet_instance where child_id = ${child} and sheet_template_id = ${t.id}
                                  order by created_at desc limit 1`)[0].qr;
  const ana = await aReadPaper(sql, {
    qr: await qr(kids.Ana), child: kids.Ana, template: t.id, items: t.items,
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", why: "under the confidence floor", guess: "7" },
            { status: "correct", read: "3", checkedBy: "e2e@cornerstone.test" }],
  });
  const bo = await aReadPaper(sql, {
    qr: await qr(kids.Bo), child: kids.Bo, template: t.id, items: t.items,
    reads: [{ status: "correct", read: "1" }, { status: "correct", read: "2" }],
  });
  const half = (pages - 1) / 2;
  const span = (from: number) => Array.from({ length: half }, (_, i) => from + i);
  const copies = [
    { copy: 1, pages: span(1), code: "ana", child_id: kids.Ana, answers: 3, capture_id: ana.capture, no_code: [], lacks: [] },
    { copy: 2, pages: span(half + 1), code: "bo", child_id: kids.Bo, answers: 2, capture_id: bo.capture, no_code: [], lacks: [] },
    { copy: 3, pages: [pages], code: "?", child_id: null, answers: 0, skipped: true, why: "no code could be read on the page", no_code: [pages] },
  ];
  await sql`update flow_run set status = 'ok', error = null, result = result || ${sql.json({ copies })} where id = ${f.id}`;

  await page.reload();
  // what the file came to, a column each (goals/uxn6-upload-papers.yaml)
  const cell = (label: string) => run.locator(`td[data-label="${label}"]`);
  await expect(cell("Pages")).toHaveText(`${pages} pages`);
  await expect(cell("Copies read")).toHaveText("2");
  await expect(cell("Answers")).toHaveText("5");
  await expect(cell("Settled by the engine")).toHaveText("3");
  await expect(cell("Checked by a person")).toHaveText("1");
  await expect(cell("Waiting")).toHaveText("1");
  await expect(run.locator("[data-status=toCheck]")).toBeVisible();
  // the blank page: said by its number, never guessed (goals/ux9a-no-guessed-pages.yaml)
  await expect(table).toContainText(`Page ${pages}: no code could be read on it, so it is not read until you say whose it is.`);
});
