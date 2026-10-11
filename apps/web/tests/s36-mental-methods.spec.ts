/**
 * Mental multiplication and division (goals/md4a-mental-methods.yaml). MD.MENTAL is taught when an educator says its
 * grade has been taught it — its topic's switch — and until then no screen shows it (goals/v1-only-what-is-taught.yaml).
 * Switched on here as an educator's word would switch it, the Question bank shows each mental method as the child meets
 * it: every step printed as the sum it works out with a blank beside it (14 × 2 = ___, 14 × 4 = ___), named in words,
 * never a code. The switch is put back.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// what each level's questions show: a step's sum and its blank, then the answer's
const SHOWS: { level: string; shows: RegExp }[] = [
  { level: "Easy", shows: /\d+ [×÷] 2 = ___[\s\S]*\d+ [×÷] [24] = ___/ },
  { level: "Medium", shows: /\d+ × \d+ = ___/ },
  { level: "Hard", shows: /\d+ × 10 = ___[\s\S]*\d+ × (9|11) = ___/ },
  { level: "Advance", shows: /\d+ × 100 = ___[\s\S]*\d+ × 25 = ___/ },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every mental method is on the Question bank, a blank for each step", async ({
  page,
}) => {
  const [topic] = await sql<{ code: string; taught: boolean }[]>`
    select t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code = 'MD.MENTAL'`;
  expect(topic, "MD.MENTAL has a topic of its own").toBeTruthy();
  expect(
    topic.taught,
    "mental multiplication and division waits for an educator's word",
  ).toBe(false);
  await sql`update topic set taught = true where code = ${topic.code}`;
  try {
    for (const k of SHOWS) {
      await page.goto(
        `/library?set=MD.MENTAL&difficulty=${k.level}&fmt=efficient_method#questions`,
      );
      const main = page.getByRole("main");
      await expect(
        main.getByText("quickest method", { exact: true }).first(),
      ).toBeVisible();
      const text = await main.getByRole("table").last().innerText();
      expect(text, k.level).toMatch(k.shows);
      expect(text, `${k.level}: a code on the page`).not.toMatch(CODE);
    }
  } finally {
    await sql`update topic set taught = false where code = ${topic.code}`;
  }
});
