/**
 * Estimating products and quotients (goals/md4b1-estimates.yaml). MD.ESTIMATE is taught when an educator says its grade
 * has been taught it — its topic's switch — and until then no screen shows it (goals/v1-only-what-is-taught.yaml).
 * Switched on here as an educator's word would switch it, the Question bank shows every estimate as the child meets it:
 * odd or even of a product, its last digit, an estimate rounded to the ten or the hundred, how many digits an answer
 * has, the closest of three estimates with its options, and whether a claimed answer could be right, named in words,
 * never a code. The switch is put back.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// what each level's questions of each kind show
const SHOWS: { level: string; fmt: string; kind: string; shows: RegExp[] }[] = [
  { level: "Easy", fmt: "odd_even", kind: "odd or even", shows: [/will \d+ × \d+ be odd or even\?/] },
  {
    level: "Easy",
    fmt: "estimate_then_calc",
    kind: "estimate, then work out",
    shows: [/say the digit \d+ × \d+ ends in/],
  },
  {
    level: "Medium",
    fmt: "estimate_then_calc",
    kind: "estimate, then work out",
    shows: [
      /Round \d+ to the nearest ten and estimate \d+ × \d+/,
      /how many digits \d+ × \d+ has/,
      /how many digits \d+ ÷ \d+ has/,
    ],
  },
  {
    level: "Hard",
    fmt: "estimate_then_calc",
    kind: "estimate, then work out",
    shows: [
      /Round both numbers to the nearest ten and estimate \d+ × \d+/,
      /Round \d+ to the nearest hundred and estimate \d+ ÷ \d+/,
    ],
  },
  {
    level: "Hard",
    fmt: "choose_estimate",
    kind: "closest estimate",
    shows: [/Which is closest to \d+ × \d+\? Do not work it out\.[\s\S]*\d+ · \d+ · \d+/],
  },
  {
    level: "Advance",
    fmt: "possible_answer",
    kind: "could it be right?",
    shows: [
      /says \d+ × \d+ = [\d,]+\. Without working it out, could that be right\?/,
      /says \d+ ÷ \d+ = \d+ r \d+\. Without working it out, could that be right\?/,
    ],
  },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every estimate is on the Question bank as the child meets it", async ({ page }) => {
  const [topic] = await sql<{ code: string; taught: boolean }[]>`
    select t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code = 'MD.ESTIMATE'`;
  expect(topic, "MD.ESTIMATE has a topic of its own").toBeTruthy();
  expect(topic.taught, "estimating products and quotients waits for an educator's word").toBe(false);
  await sql`update topic set taught = true where code = ${topic.code}`;
  try {
    for (const k of SHOWS) {
      await page.goto(`/library?set=MD.ESTIMATE&difficulty=${k.level}&fmt=${k.fmt}#questions`);
      const main = page.getByRole("main");
      await expect(main.getByText(k.kind, { exact: true }).first()).toBeVisible();
      const text = await main.getByRole("table").last().innerText();
      for (const shows of k.shows) expect(text, `${k.level} ${k.fmt}`).toMatch(shows);
      expect(text, `${k.level} ${k.fmt}: a code on the page`).not.toMatch(CODE);
    }
  } finally {
    await sql`update topic set taught = false where code = ${topic.code}`;
  }
});
