/**
 * Division as four skills (goals/md3a-straight-division.yaml). DIV.FACTS, DIV.TENS, DIV.2D1D and DIV.3D1D are taught
 * when an educator says their grade has been taught them — their topic's switch — and until then no screen shows them
 * (goals/v1-only-what-is-taught.yaml). Switched on here as an educator's word would switch it, the Question bank shows
 * a division in the division layout, the quotient's blanks above the number divided, and one that leaves a remainder
 * with a blank of its own after "r" — named in words, never a code. The switch is put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, a division is on the Question bank in its layout, a box for its remainder", async ({ page }) => {
  const topics = await sql<{ code: string; taught: boolean }[]>`
    select distinct t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code in ('DIV.2D1D', 'DIV.3D1D')`;
  expect(topics.length, "division in a topic of its own").toBeGreaterThan(0);
  expect(topics.every((t) => !t.taught), "division waits for an educator's word").toBe(true);
  await sql`update topic set taught = true where code = any(${topics.map((t) => t.code)})`;
  try {
    // A page arrives after its skeleton (app/(app)/loading.tsx), some 200ms after `goto` returns: each read waits for
    // what it is about. Read at once, the main area held the skeleton and no table (19 runs in 30, from the twelfth).
    await page.goto(`/library?set=DIV.3D1D&fmt=column_grid#questions`);
    const laid = page.getByRole("main").getByRole("table").last();
    await expect(
      laid.getByRole("img", { name: /^\d+ ÷ \d+ in the division layout$/ }).first(),
      "the division layout is drawn",
    ).toBeVisible();
    expect(await laid.innerText(), "a code on the page").not.toMatch(CODE);

    await page.goto(`/library?set=DIV.2D1D&fmt=bare_sum#questions`);
    const listed = page.getByRole("main").getByRole("table").last();
    await expect(listed, "a remainder's own blank after r").toContainText(/\d+ ÷ \d+ = ___ r ___/, {
      useInnerText: true,
    });
    expect(await listed.innerText(), "a code on the page").not.toMatch(CODE);
  } finally {
    await sql`update topic set taught = false where code = any(${topics.map((t) => t.code)})`;
  }
});
