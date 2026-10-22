/**
 * M5d: the website draws every kind of × and ÷ question the bank holds (goals/md5d-every-kind-draws.yaml). For every
 * skill set of ×, ÷ and both, and every kind of question it has, its topic switched on as an educator's word would
 * switch it, the Question bank lists its questions: each shows its numbers — written, or drawn in a picture whose label
 * says them (a tally, rows of dots, a grid) — never "undefined", "NaN", "null" or a code; and the kind has a name in the
 * school's words, which is what puts it among the kinds an educator can pick. The topics are put back as they were.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const BROKEN = /\bundefined\b|\bNaN\b|\bnull\b|\[object Object\]/;
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

// A topic switched on is taught in each class that has not said otherwise (`skill_taught_in`), so its questions show
// only where a class is on the roll: the class is this spec's own, as a fresh copy has none (`bin/testdb fresh`).
test.beforeAll(async () => {
  await aClass(sql, "M5-TEST", "G2", ["Asha"]);
});

test.afterAll(async () => {
  await sql.end();
});

test("every kind of × and ÷ question the bank holds is drawn with its numbers, in the school's words", async ({ page }) => {
  test.setTimeout(600_000);
  const pairs = await sql<{ set: string; fmt: string }[]>`
    select distinct skill_set_code as set, fmt from item
    where status = 'active' and split_part(skill_set_code, '.', 1) in ('MUL', 'DIV', 'MD') order by 1, 2`;
  expect(pairs.length, "the bank holds × and ÷ questions").toBeGreaterThan(0);
  const skills = await sql<{ code: string; taught: boolean }[]>`
    select distinct s.code, s.taught from skill_set s
    where split_part(s.code, '.', 1) in ('MUL', 'DIV', 'MD')`;
  await sql`update skill_set set taught = true where code = any(${skills.map((t) => t.code)})`;
  const wrong: string[] = [];
  try {
    const pickable = new Map<string, (string | null)[]>();
    for (const { set, fmt } of pairs) {
      if (!pickable.has(set)) {
        // the kinds an educator can pick, on the skill set's page with none picked: only their chips carry a kind, and
        // only a kind with a name in the school's words (`question_type.words`) has one
        await page.goto(`/library?set=${set}#questions`);
        // read once the page has streamed in, not at its frame
        await expect(page.locator("#questions")).toBeVisible();
        const hrefs = await page.locator("#questions a[href]").evaluateAll((els) => els.map((e) => e.getAttribute("href") ?? ""));
        pickable.set(set, hrefs.map((h) => new URL(h, "http://x").searchParams.get("fmt")));
      }
      if (!pickable.get(set)!.includes(fmt)) wrong.push(`${set} ${fmt}: no name in the school's words, so no kind to pick`);
      await page.goto(`/library?set=${set}&fmt=${fmt}#questions`);
      // read once the page has streamed in, not at its frame
      await expect(page.locator("#questions")).toBeVisible();
      const rows = page.locator("#questions table tbody tr");
      const n = await rows.count();
      if (!n) wrong.push(`${set} ${fmt}: no question listed`);
      for (let i = 0; i < n; i++) {
        const cell = rows.nth(i).locator("td").first();
        const labels = await cell.locator("[aria-label]").evaluateAll((els) => els.map((e) => e.getAttribute("aria-label")));
        const shown = `${await cell.innerText()} ${labels.join(" ")}`;
        const said = shown.slice(0, 80);
        if (!/\d/.test(shown)) wrong.push(`${set} ${fmt}: a question with no number — ${said}`);
        if (BROKEN.test(shown)) wrong.push(`${set} ${fmt}: "${shown.match(BROKEN)![0]}" — ${said}`);
        if (CODE.test(shown)) wrong.push(`${set} ${fmt}: a code, ${shown.match(CODE)![0]}`);
      }
    }
  } finally {
    for (const t of skills) await sql`update skill_set set taught = ${t.taught} where code = ${t.code}`;
  }
  expect([...new Set(wrong)], "every × ÷ question drawn with its numbers").toEqual([]);
});
