/**
 * The tables' Advance kinds, × and ÷ (goals/md3b1-facts-advance.yaml). MUL.FACTS and DIV.FACTS are taught when an
 * educator says their grade has been taught them — their topic's switch — and until then no screen shows them
 * (goals/v1-only-what-is-taught.yaml). Switched on here as an educator's word would switch it, the Question bank shows
 * each kind with its own numbers: a missing factor as its sentence, a fact family as its three facts, and the table
 * backwards as both of its sentences, the division and the fact — named in words, never a code. The switch is put
 * back after.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

async function shown(page: Page, set: string, fmt: string) {
  await page.goto(`/library?set=${set}&fmt=${fmt}#questions`);
  const text = await page.getByRole("main").getByRole("table").last().innerText();
  expect(text, "a code on the page").not.toMatch(CODE);
  return text;
}

test("once taught, the tables' kinds are on the Question bank with their numbers", async ({ page }) => {
  const topics = await sql<{ code: string; taught: boolean }[]>`
    select distinct t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code in ('MUL.FACTS', 'DIV.FACTS')`;
  expect(topics.length, "the tables in topics of their own").toBeGreaterThan(0);
  expect(topics.every((t) => !t.taught), "the tables wait for an educator's word").toBe(true);
  await sql`update topic set taught = true where code = any(${topics.map((t) => t.code)})`;
  try {
    expect(await shown(page, "MUL.FACTS", "missing_number"), "a missing factor's sentence").toMatch(
      /(\d+|□) × (\d+|□) = \d+/,
    );
    expect(await shown(page, "MUL.FACTS", "fact_family"), "a fact family's divisions").toMatch(/\d+ ÷ \d+ = □/);
    expect(await shown(page, "DIV.FACTS", "inverse_check"), "the table backwards: the division and its fact").toMatch(
      /\d+ ÷ \d+ = □[\s\S]*\d+ × □ = \d+/,
    );
  } finally {
    await sql`update topic set taught = false where code = any(${topics.map((t) => t.code)})`;
  }
});
