/**
 * Check answers is quick again (goals/perf-slow-site.yaml, docs/notes/perf-slow-site.md).
 *
 * Nimish, 2026-10-26: "Once I click what the child has written, it literally takes a few seconds to go to the next one.
 * This wasn't the case previously." — "slow on all clicks". The screen as he saw it: 80 answers waiting over 12 papers,
 * each paper a copy cut from one scan file, two photographed pages each. Each test measures one request the way he
 * makes it and holds it to a budget of time. The timings are this machine's, never live's.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper, aWorksheet } from "./rows";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 1 });
test.afterAll(async () => sql.end());

// A click took about 8 seconds on 80 answers here before the fix and 0.3 after; CI's machines are slower, so the budget
// is wide of the one and far short of the other.
const BUDGET = 2500;
const SCAN = path.join(tmpdir(), "P6-SCAN");
const KIDS = Array.from({ length: 12 }, (_, i) => `P6 child ${i + 1}`);
const code = (k: number) => `CS${(0xe60000 + k).toString(16).toUpperCase()}`;
const copyFile = (k: number) => path.join(SCAN, `copy${String(k).padStart(2, "0")}-p1-${code(k)}.pdf`);

// Each copy as a phone takes it: two pages, each a 12-megapixel photograph on an A4 page, its code printed in the corner.
const PHOTOS = `
import sys, numpy as np, cv2, pymupdf, segno, io
for f, code in zip(sys.argv[1::2], sys.argv[2::2]):
    doc = pymupdf.open()
    for p in (1, 2):
        rng = np.random.default_rng(abs(hash((code, p))) % 2**32)
        img = np.clip(225 + rng.normal(0, 12, (4032, 3024, 3)), 0, 255).astype(np.uint8)
        buf = io.BytesIO(); segno.make(code, error="h").save(buf, kind="png", scale=18, border=2)
        qr = cv2.imdecode(np.frombuffer(buf.getvalue(), np.uint8), cv2.IMREAD_COLOR)
        img[150:150 + qr.shape[0], 2700 - qr.shape[1]:2700] = qr
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes())
    doc.save(f)
`;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  rmSync(SCAN, { recursive: true, force: true });
  mkdirSync(SCAN, { recursive: true });
  const python = path.resolve(__dirname, "../../../packages/engine/.venv/bin/python");
  execFileSync(python, ["-c", PHOTOS, ...KIDS.flatMap((_, i) => [copyFile(i + 1), code(i + 1)])]);
  const kids = await aClass(sql, "P6-TEST", "G2", KIDS);
  const sums = ["46 + 38", "57 + 28", "68 + 27", "59 + 24", "35 + 47", "26 + 18", "33 + 29", "47 + 45"];
  const w = await aWorksheet(sql, {
    code: "P6-A", title: "P6 paper", date: "2026-10-20", band: "G2", week: "P6-TEST",
    items: sums.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
  });
  // 80 answers to check (8 papers of 7, 4 of 6) and a spot-check each, as the screen showed it
  for (const [i, name] of KIDS.entries()) {
    const waiting = i < 8 ? 7 : 6;
    const reads = sums.map((_, n) =>
      n < waiting
        ? { status: "unreadable", why: "not sure of the digits", guess: "84", box: [0.1, 0.2, 0.5, 0.3] }
        : { status: "correct", read: "82" },
    );
    const p = await aReadPaper(sql, { qr: code(i + 1), child: kids[name], template: w.template, items: w.items, reads, file: copyFile(i + 1) });
    await sql`update capture set pages = 2 where id = ${p.capture}`;
  }
  await sql`analyze`;
});

/** One request measured, end to end: the time until the next screen shows. A note between two markers in the database's
 *  log lets the statements it cost be counted there (docs/notes/perf-slow-site.md); nothing here depends on them. */
async function measured(what: string, go: () => Promise<unknown>): Promise<number> {
  await sql`select ${`p6 start: ${what}`}::text`;
  const t = Date.now();
  await go();
  const ms = Date.now() - t;
  await sql`select ${`p6 end: ${what}`}::text`;
  console.log(`p6 | ${what} | ${ms} ms`);
  return ms;
}

const open = (page: Page, url: string) => async () => {
  await page.goto(url);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
};

test("the check screen opens on 80 answers within its budget", async ({ page }) => {
  await open(page, "/capture/check")(); // the build's first request warms its own code, once
  const ms = await measured("open /capture/check", open(page, "/capture/check"));
  await expect(page.getByText(/\d+ answers left to check/)).toBeVisible();
  expect(ms).toBeLessThan(BUDGET);
});

test("one click of Yes shows the next answer within its budget", async ({ page }) => {
  // the first answer waiting on the test's own first paper, put back afterwards as it was
  const [r] = await sql<{ id: string; status: string; state: string; misconception_codes: string[]; working_shown: string }[]>`
    select r.id, r.status, r.state, r.misconception_codes, r.working_shown from item_result r join capture c on c.id = r.capture_id
    where c.path = ${copyFile(1)} and c.superseded_by is null and r.status = 'unreadable' order by r.created_at, r.id limit 1`;
  try {
    await page.goto(`/capture/check?id=${r.id}`);
    const left = page.getByText(/\d+ answers left to check/);
    const n = Number((await left.textContent())?.match(/\d+/)?.[0]);
    const ms = await measured("click Yes, the child wrote 84", async () => {
      await page.getByRole("button", { name: "Yes, the child wrote 84" }).click();
      await expect(page.getByText(`${n - 1} answers left to check`)).toBeVisible();
    });
    expect(ms).toBeLessThan(BUDGET);
  } finally {
    await sql`delete from read_correction where item_result_id = ${r.id} and by = ${TEST_STAFF.email}`;
    await sql`update item_result set status = ${r.status}, state = ${r.state}, misconception_codes = ${r.misconception_codes},
              working_shown = ${r.working_shown} where id = ${r.id}`;
  }
});

test("the five most-used pages open within their budget", async ({ page }) => {
  for (const [name, url] of [
    ["What needs doing", "/today"],
    ["Children", "/school"],
    ["Assessments", "/papers"],
    ["Results", "/growth"],
    ["Skills", "/"],
  ] as const) {
    await open(page, url)();
    expect(await measured(`open ${url} (${name})`, open(page, url)), name).toBeLessThan(BUDGET);
  }
});
