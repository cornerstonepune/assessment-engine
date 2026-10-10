/**
 * The column skills' Advance, ÷ (goals/md3b2-divide-advance.yaml). DIV.2D1D and DIV.3D1D are taught when an educator
 * says their grade has been taught them — their topic's switch — and until then no screen shows them
 * (goals/v1-only-what-is-taught.yaml). Switched on here as an educator's word would switch it, the Question bank shows
 * each Advance kind with its own numbers: a digit missing in the number divided, the remainder or the divisor missing,
 * a claimed answer to judge, a check by multiplying, how many digits a quotient has or the number divided rounded, and
 * ÷ 5 as ÷ 10 then doubled — named in words, never a code. The switch is put back after.
 *
 * And the last of them (goals/md3b3-divide-mistakes-and-stories.yaml): a worked division whose mistake the child finds,
 * named on the Question bank by the mistake's own row — the words the school edits, which no code carries a copy of —
 * and the stories that use what is left over.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

// A page arrives after its skeleton (app/(app)/loading.tsx), some 200ms after `goto` returns: the assertion waits for
// the questions it is about, never reads the main area once.
async function shows(page: Page, set: string, fmt: string, says: RegExp, what: string) {
  await page.goto(`/library?set=${set}&difficulty=Advance&fmt=${fmt}#questions`);
  const listed = page.getByRole("main").getByRole("table").last();
  await expect(listed, what).toContainText(says, { useInnerText: true });
  expect(await listed.innerText(), "a code on the page").not.toMatch(CODE);
}

test("once taught, the column skills' Advance kinds are on the Question bank with their numbers", async ({ page }) => {
  const topics = await sql<{ code: string; taught: boolean }[]>`
    select distinct t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code in ('DIV.2D1D', 'DIV.3D1D')`;
  expect(topics.length, "division in a topic of its own").toBeGreaterThan(0);
  expect(topics.every((t) => !t.taught), "division waits for an educator's word").toBe(true);
  await sql`update topic set taught = true where code = any(${topics.map((t) => t.code)})`;
  try {
    await shows(page, "DIV.2D1D", "missing_digit", /\d*□\d* ÷ \d+ = \d+/, "a digit missing in the number divided");
    await shows(page, "DIV.2D1D", "missing_number", /\d+ ÷ (\d+|□) = \d+ r (\d+|□)/, "the remainder or divisor missing");
    await shows(page, "DIV.2D1D", "possible_answer", /\d+ ÷ \d+ = \d+ r \d+/, "a claimed answer to judge");
    await shows(page, "DIV.2D1D", "inverse_check", /\d+ × \d+( \+ \d+)? = □/, "the check by multiplying");
    await shows(page, "DIV.3D1D", "estimate_then_calc", /how many digits \d+ ÷ \d+|nearest hundred/, "an estimate");
    await shows(page, "DIV.3D1D", "efficient_method", /\d+ ÷ 10/, "÷ 5 as ÷ 10 then doubled");
  } finally {
    await sql`update topic set taught = false where code = any(${topics.map((t) => t.code)})`;
  }
});

test("a worked division's mistake is named on the Question bank by its row", async ({ page }) => {
  const topics = await sql<{ code: string }[]>`
    select distinct t.code from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code in ('DIV.2D1D', 'DIV.3D1D')`;
  // each mistake a worked division shows, by its row: what the Question bank must call it
  const rows = await sql<{ code: string; name: string }[]>`
    select code, name from misconception
    where op = '÷' and code in ('M_DIV_REMAINDER_TOO_BIG', 'M_DIV_QUOTIENT_ZERO_DROPPED', 'M_DIV_BRING_DOWN_MISSED')`;
  expect(rows.length, "each mistake a worked division shows has its row").toBe(3);
  const name = Object.fromEntries(rows.map((r) => [r.code, r.name]));
  await sql`update topic set taught = true where code = any(${topics.map((t) => t.code)})`;
  try {
    const worked = /\d+ ÷ \d+ and wrote \d+( r \d+)?/;
    for (const [set, planted] of [
      ["DIV.2D1D", [name.M_DIV_REMAINDER_TOO_BIG]],
      ["DIV.3D1D", [name.M_DIV_QUOTIENT_ZERO_DROPPED, name.M_DIV_BRING_DOWN_MISSED]],
    ] as const) {
      await shows(page, set, "find_mistake", worked, `a worked division on ${set}`);
      // the question's own page: its planted mistake among the wrong answers it catches, named by its row, and the why
      // read against it, no name copied into the question
      const [one] = await sql<{ item_key: string }[]>`
        select item_key from item where skill_set_code = ${set} and difficulty = 'Advance' and fmt = 'find_mistake'
          and status = 'active' order by item_key limit 1`;
      await page.goto(`/library/${one.item_key}`);
      const caught = page.getByRole("table", { name: "Wrong answers it catches" });
      await expect(caught).toContainText(new RegExp(planted.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")));
      await expect(page.getByRole("main")).toContainText("Looks for: Names the mistake its worked answer shows");
      expect(await page.getByRole("main").innerText(), "a code on the page").not.toMatch(CODE);
    }
    await shows(page, "DIV.2D1D", "word_1step", /left over|full|needed/, "a story that uses what is left over");
  } finally {
    await sql`update topic set taught = false where code = any(${topics.map((t) => t.code)})`;
  }
});
