/**
 * U61 — A paper's page 2 is never page 1 drawn again (goals/img_page_one_and_two_same_photo.yaml). Nimish, 2026-10-23:
 * on the check screen of one child's paper from the 20-page Grade 1 file, "The whole page" showed "Page 1, as it was
 * photographed" and a second photograph that looked the same, though page 2 holds other questions (9 to 12).
 *
 * Three papers of the test's own, each a pair of pages in a file on the engine's disk (synthetic pages, no scan):
 *  - read before the engine could refuse a repeat: its file's page 2 is page 1's photograph again;
 *  - read after: page 2's answers wait for a person with the reason in words, and the file holds one page;
 *  - two different pages: both are drawn, and they are two different images.
 * Set IMG_SHOTS to a folder to keep a 1440 px picture of each (the before and after of the report).
 */
import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U61-PAGES";
const PY = path.resolve(__dirname, "../../../packages/engine/.venv/bin/python");
let kids: Record<string, string>;
let work: { id: string; item_ids: string[] };
let dir: string;

/** A pdf of pages that each print `texts[i]` in large letters: synthetic, so two of the same text are one photograph. */
function pdf(name: string, texts: string[]): string {
  const out = path.join(dir, name);
  execFileSync(PY, [
    "-I",
    "-c",
    [
      "import sys, pymupdf",
      "doc = pymupdf.open()",
      "for t in sys.argv[2:]:",
      "    p = doc.new_page(width=595, height=842)",
      "    for i, line in enumerate(t.split('|')):",
      "        p.insert_text((60, 120 + i * 60), line, fontsize=28)",
      "doc.save(sys.argv[1])",
    ].join("\n"),
    out,
    ...texts,
  ]);
  return out;
}

const PAGE1 = "Equal groups|Page one|Questions 1 to 8";
const PAGE2 = "Equal groups|Page two|Questions 9 to 12";

/** One paper of four answers, two on each page, the way the reader leaves them; `page2` rewrites the last two. */
async function aPaper(who: string, qr: string, file: string, page2: (id: string) => Promise<void>): Promise<string> {
  const { sheet, results } = await aReadPaper(sql, {
    qr,
    child: kids[who],
    template: work.id,
    items: work.item_ids.slice(0, 4),
    reads: [
      { status: "needs_teacher", read: "4", why: "a person checks it" },
      { status: "needs_teacher", read: "6", why: "a person checks it" },
      { status: "needs_teacher", read: "9", why: "a person checks it" },
      { status: "needs_teacher", read: "2", why: "a person checks it" },
    ],
    file,
  });
  for (const [i, id] of results.entries()) {
    const at = i < 2 ? { page: 1, file_page: 1 } : { page: 2, file_page: 2 };
    await sql`update item_result set raw_read = (raw_read::jsonb || ${sql.json(at)})::text where id = ${id}`;
  }
  await page2(results.slice(2).join(","));
  return sheet;
}

async function shoot(page: Page, name: string): Promise<void> {
  if (!process.env.IMG_SHOTS) return;
  mkdirSync(process.env.IMG_SHOTS, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(process.env.IMG_SHOTS, `${name}.png`), fullPage: true });
}

test.beforeAll(async () => {
  dir = mkdtempSync(path.join(tmpdir(), "u61-"));
  kids = await aClass(sql, SECTION, "G1", ["Kavya", "Mohan", "Neel"]);
  [work] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where source = 'library' and retired_at is null
      and array_length(item_ids, 1) >= 4 order by code limit 1`;
});

test("a reading made before: page 2 that is page 1 again is not drawn, and the screen says page 2 is not found", async ({ page }) => {
  const sheet = await aPaper("Kavya", "CS61A001", pdf("again.pdf", [PAGE1, PAGE1]), async () => {});
  await page.goto(`/capture/${sheet}`);
  await shoot(page, "before-and-after-a-reading-made-before");
  const panel = page.locator("section", { has: page.getByRole("heading", { name: "The whole page" }) });
  await expect(panel.getByText("Page 2 not found. The photograph in its place is page 1 again.")).toBeVisible();
  await expect(panel.locator("img")).toHaveCount(1);
  await expect(panel.locator("img").first()).toHaveAttribute("alt", "Page 1 of the paper");
});

test("a reading made after: page 2's answers wait for a person and no photograph is drawn for it", async ({ page }) => {
  const sheet = await aPaper("Mohan", "CS61A002", pdf("one.pdf", [PAGE1]), async (ids) => {
    for (const id of ids.split(",")) {
      const lost = { answer_state: "not_found", child_answer: "", page: 2, page_found: false, why: "page 2 not found: no photograph of it is in the file" };
      await sql`update item_result set raw_read = ${sql.json(lost)}::text, status = 'unreadable' where id = ${id}`;
    }
  });
  await page.goto(`/capture/${sheet}`);
  await shoot(page, "after-a-reading-made-after");
  const panel = page.locator("section", { has: page.getByRole("heading", { name: "The whole page" }) });
  await expect(panel.getByText("Page 2 not found. No photograph of it is in the file.")).toBeVisible();
  await expect(panel.locator("img")).toHaveCount(1);
});

test("two different pages are both drawn, as two different images", async ({ page }) => {
  const sheet = await aPaper("Neel", "CS61A003", pdf("both.pdf", [PAGE1, PAGE2]), async () => {});
  await page.goto(`/capture/${sheet}`);
  await shoot(page, "two-different-pages");
  const panel = page.locator("section", { has: page.getByRole("heading", { name: "The whole page" }) });
  await expect(panel.getByText(/not found/)).toHaveCount(0);
  const pics = panel.locator("img");
  await expect(pics).toHaveCount(2);
  const bytes = [];
  for (const i of [0, 1]) {
    const res = await page.request.get((await pics.nth(i).getAttribute("src"))!);
    expect(res.ok()).toBe(true);
    bytes.push((await res.body()).toString("base64"));
  }
  expect(bytes[0]).not.toEqual(bytes[1]);
});
