/**
 * Whose paper is it (goals/chk_whose_paper.yaml). Nimish, 2026-10-23: "a very clear mechanism for marking this per child",
 * and "that mark, this as right ... should be in that same box where we are asking whether it is what the child wrote".
 *
 * The papers are the test's own (tests/rows.ts): three children of one class cut from one scanned file — Mahishmati's copy
 * 1, Bina's copy 2 holding copy 1's very photograph, Chitra's copy 3 — and a fourth, alone in a class of her own.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper, aWorksheet } from "./rows";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

const SCANS = path.join(tmpdir(), "s44-whose-paper");
const PYTHON = path.resolve(__dirname, "../../../packages/engine/.venv/bin/python");
const SHOTS = path.resolve(__dirname, "../test-results/whose-paper");
// A scan: one photograph per page, each the QR of the text given — the same text on two pages is the same photograph.
const scan = (file: string, text: string) => {
  mkdirSync(path.dirname(file), { recursive: true });
  execFileSync(PYTHON, ["-I", "-c", `
import io, sys, pymupdf, segno
buf = io.BytesIO(); segno.make(sys.argv[2], error="h").save(buf, kind="png", scale=9, border=4)
doc = pymupdf.open(); page = doc.new_page(); page.insert_image(page.rect, stream=buf.getvalue()); doc.save(sys.argv[1])
`, file, text]);
  return file;
};

type Ids = { sheet: string; capture: string; results: string[] };
const made: Record<string, Ids> = {};

test.beforeAll(async () => {
  const kids = await aClass(sql, "S44-TEST", "G1", ["Mahishmati", "Bina", "Chitra", "Esha"]);
  const alone = await aClass(sql, "S44-ALONE", "G1", ["Devi"]);
  const sums = ["4 + 3", "5 + 2", "6 + 3"];
  const sheet = (code: string, week: string) =>
    aWorksheet(sql, {
      code, title: "S44 paper", date: "2026-10-21", band: "G1", week,
      items: sums.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
    });
  const [w, w2] = [await sheet("S44-A", "S44-TEST"), await sheet("S44-B", "S44-ALONE")];
  // each question its own printed box (`boxes: 1`), or the screen shows the whole page and outlines nothing
  const unsure = (guess: string, n: number) => ({ status: "unreadable", why: "not sure of the digits", guess, box: [0.1, 0.2 * n, 0.5, 0.2 * n + 0.1], boxes: 1 });
  const copy = async (k: number, qr: string, text: string, child: string, t: typeof w, reads: Parameters<typeof aReadPaper>[1]["reads"]) =>
    (made[qr] = await aReadPaper(sql, { qr, child, template: t.template, items: t.items, reads, file: scan(path.join(SCANS, "scan-1", `copy0${k}-p1-${qr}.pdf`), text) }));
  await copy(1, "CSA00001", "CSA00001", kids.Mahishmati, w, [unsure("7", 1), unsure("7", 2), { status: "correct", read: "9" }]);
  await copy(2, "CSA00002", "CSA00001", kids.Bina, w, [unsure("7", 1), { status: "correct", read: "7" }, { status: "correct", read: "9" }]); // copy 1's photograph
  await copy(3, "CSA00003", "CSA00003", kids.Chitra, w, [{ status: "correct", read: "7" }, { status: "correct", read: "7" }, { status: "correct", read: "9" }]);
  await copy(4, "CSA00005", "CSA00005", kids.Esha, w, [unsure("7", 1), { status: "correct", read: "7" }, { status: "correct", read: "9" }]);
  await copy(1, "CSA00004", "CSA00004", alone.Devi, w2, [{ status: "correct", read: "7" }, { status: "correct", read: "7" }, { status: "wrong", read: "8", checkedBy: "rows.ts" }]);
});

const open = async (page: import("@playwright/test").Page, qr: string, n: number) => {
  await page.goto(`/capture/check?id=${made[qr].results[n]}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check answers");
};

test("the Yes button is in the answer box, under the sentence it answers; nothing sits above the card but the progress line", async ({ page }) => {
  await open(page, "CSA00001", 0);
  const box = page.locator(".grid.content-start", { hasText: "The reader thinks the child wrote" });
  await expect(box.getByText("The reader thinks the child wrote")).toBeVisible();
  const yes = box.getByRole("button", { name: "Yes, the child wrote 7" });
  await expect(yes).toBeVisible();
  await expect(box.getByRole("button", { name: "Save" })).toBeVisible();
  await expect(box.getByRole("button", { name: "Nothing is written here" })).toBeVisible();
  // under the sentence, not above the card
  const [said, button] = [await box.getByText("The reader thinks the child wrote").boundingBox(), await yes.boundingBox()];
  expect(button!.y).toBeGreaterThan(said!.y);
  await expect(page.locator("[data-ux=action] button")).toHaveCount(0);
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, "after-card.png") });
});

test("beside the crop, the page's own proof: the page with the crop outlined, the printed code, the copy and the page", async ({ page }) => {
  await open(page, "CSA00001", 0);
  await expect(page.locator("h2, h3, [class*=panel]").filter({ hasText: "Mahishmati · paper CSA00001 · answer 1 of 3 · 2 left" }).first()).toBeVisible();
  const proof = page.getByRole("complementary", { name: "Whose paper this page is" });
  await expect(proof.getByText("CSA00001").first()).toBeVisible();
  await expect(proof.getByText("Copy 1 of 4 in this file · page 1 of 1")).toBeVisible();
  await expect(proof.getByTestId("crop-outline")).toBeVisible();
  const thumb = proof.getByRole("img");
  await expect.poll(() => thumb.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0);
  // a copy whose photograph is its own carries no notice
  await open(page, "CSA00005", 0);
  await expect(page.getByText("Esha · paper CSA00005")).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Whose paper this page is" }).getByText("same picture")).toHaveCount(0);
  await expect(page.getByText("Copy 4 of 4 in this file · page 1 of 1")).toBeVisible();
});

test("checking runs per child: a next-child step only when this child is done, and a list of the file's children with answers left", async ({ page }) => {
  await open(page, "CSA00001", 0);
  await expect(page.locator("[data-ux=next]")).toHaveText(/next answer of this paper/);
  const list = page.getByRole("table", { name: /^Papers of / });
  await expect(list.getByRole("row", { name: /^1 .* CSA00001 3 / })).toBeVisible();
  await expect(list.getByRole("row", { name: /^2 .* CSA00002 2 / })).toBeVisible();
  await open(page, "CSA00001", 1);
  await expect(page.locator("[data-ux=next]")).toHaveText(/next answer of this paper/);
  await expect(page.getByText("answer 2 of 3 · 1 left")).toBeVisible();
  // Bina has two answers waiting: on the second, her paper is done, and only then is the next paper offered
  await page.getByRole("table", { name: /^Papers of / }).getByRole("row", { name: /CSA00002/ }).getByRole("link", { name: "Check this" }).click();
  await expect(page.getByText("answer 1 of 2 · 1 left")).toBeVisible();
  await page.locator("[data-ux=next]").click();
  await expect(page.getByText("answer 2 of 2 · 0 left")).toBeVisible();
  await expect(page.locator("[data-ux=next]")).toHaveText(/Next paper in this assessment|This assessment is done — next assessment/);
});

test("the same photograph on two children's copies is a plain red notice, and Yes waits for a person", async ({ page }) => {
  await open(page, "CSA00002", 0);
  const proof = page.getByRole("complementary", { name: "Whose paper this page is" });
  await expect(proof.getByText(/same picture as a page of copy 1 in this file/)).toBeVisible();
  const yes = page.getByRole("button", { name: "Yes, the child wrote 7" });
  await expect(yes).toBeDisabled();
  await page.screenshot({ path: path.join(SHOTS, "same-photograph.png") });
  await proof.getByRole("button", { name: "This page is Bina’s" }).click();
  await expect(proof.getByText("e2e@cornerstone.test said this page is Bina’s.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Yes, the child wrote 7" })).toBeEnabled();
  // nothing was edited: the choice is a row of its own
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from page_choice where capture_id = ${made.CSA00002.capture}`;
  expect(n).toBe(1);
  // and a copy with its own photograph has no notice
});

test("signing a paper off says the score recorded, and the last paper of an assessment links to its Results", async ({ page }) => {
  for (const [qr, child, score] of [["CSA00003", "Chitra", "3 of 3"], ["CSA00004", "Devi", "2 of 3"]] as const) {
    await page.goto(`/capture/${made[qr].sheet}`);
    await page.getByRole("button", { name: /^Sign off \d+ answers? as/ }).click();
    await expect(page.getByText(`Scores recorded for ${child}: ${score.replace(" of ", " of ")} right.`)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("link", { name: `${child}’s page →` })).toBeVisible();
    if (qr === "CSA00003") await expect(page.getByText("Every paper of this assessment is signed off")).toHaveCount(0); // copies 1 and 2 wait
    else {
      await expect(page.getByRole("link", { name: "See its Results →" })).toHaveAttribute("href", /\/papers\/card\?class=S44-ALONE/);
      await page.screenshot({ path: path.join(SHOTS, "scores-recorded.png") });
    }
  }
  // the score is where an educator looks: the assessment's row, and its card
  await page.goto("/papers/card?class=S44-ALONE&week=S44-ALONE&kind=earlier");
  await expect(page.getByText("2 of 3").first()).toBeVisible();
  // and on the Children page, which used to show learning gaps and nothing of the paper just signed off
  // (a class chosen in the filter row lists all its children, each row with the score of its last paper)
  await page.goto("/growth?class=S44-TEST");
  const row = (who: string) => page.getByRole("row").filter({ has: page.getByRole("link", { name: who, exact: true }) });
  await expect(row("Chitra")).toContainText("3 of 3 right");
  // a child with no paper signed off has no score, not "0 of 0"
  await expect(row("Bina")).not.toContainText("right");
  await page.goto("/growth?class=S44-ALONE");
  await expect(row("Devi")).toContainText("2 of 3 right");
});
