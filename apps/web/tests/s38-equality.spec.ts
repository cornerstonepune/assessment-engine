/**
 * Equations with × and ÷ (goals/md4b2-equality.yaml). MD.EQUALITY is taught when an educator says its grade has been
 * taught it — its topic's switch — and until then no screen shows it (goals/v1-only-what-is-taught.yaml). Switched on
 * here as an educator's word would switch it, the Question bank shows every equation as the child meets it: each
 * sentence with its own box or its own tick, a product turned round, × 1 and ÷ 1, a number ÷ itself and 0 ÷ a number,
 * true or false beside its other, three numbers grouped either way, a factor doubled or partitioned, a balance against
 * − and against ÷, the missing sign, a comparison, a remainder checked by multiplying back and a wrong answer explained
 * by it — every mistake named in words, never a code. The switch is put back.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// what each level's questions of each kind show, across every page of them
const SHOWS: { level: string; fmt: string; kind: string; shows: RegExp[] }[] = [
  {
    level: "Easy",
    fmt: "equation",
    kind: "make both sides equal",
    shows: [
      /(\d+) × (\d+) = \2 × □/,
      /(\d+) × 1 = □ and \1 ÷ 1 = □/,
      /(\d+) ÷ \1 = □ and 0 ÷ \1 = □/,
      /(\d+) × (\d+) = \2 × \1/,
      /(\d+) − (\d+) = \2 − \1/,
    ],
  },
  {
    level: "Medium",
    fmt: "equation",
    kind: "make both sides equal",
    shows: [
      /\((\d+) × (\d+)\) × (\d+) = \1 × \(\2 × \3\) = □/,
      /(\d+) × (\d+) = \d+, so \1 × \d+ = □/,
    ],
  },
  {
    level: "Medium",
    fmt: "inverse_check",
    kind: "check with the inverse",
    shows: [/Check \d+ ÷ \d+ = \d+/],
  },
  {
    level: "Hard",
    fmt: "equation",
    kind: "make both sides equal",
    shows: [
      /(\d+) × \d+ = \1 × 10 \+ \1 × □/,
      /\d+ × \d+ = \d+ − □/,
      /\d+ × \d+ = \d+ ÷ □/,
      /\d+ □ \d+ = \d+/,
      /(\d+) × \d+ ○ \1 × \d+/,
      /(\d+) ÷ \d+ ○ \1 ÷ \d+/,
    ],
  },
  {
    level: "Advance",
    fmt: "equation",
    kind: "make both sides equal",
    shows: [
      /(\d+) ÷ 0 = 0 and 0 ÷ \1 = 0|0 ÷ (\d+) = 0 and \2 ÷ 0 = 0/,
      /(\d+) ÷ (\d+) = \2 ÷ \1/,
      /(\d+) × (\d+) = \2 × \1/,
    ],
  },
  {
    level: "Advance",
    fmt: "inverse_check",
    kind: "check with the inverse",
    shows: [/Check \d+ ÷ \d+ = \d+ r \d+/, /\d+ × \d+ \+ \d+ = □/],
  },
  {
    level: "Advance",
    fmt: "explain_claim",
    kind: "explain a claim",
    shows: [/says \d+ ÷ \d+ = \d+\. Multiply back/, /\d+ × \d+ = □/],
  },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every equation is on the Question bank as the child meets it", async ({ page }) => {
  const [skill] = await sql<{ code: string; taught: boolean }[]>`
    select s.code, s.taught from skill_set s
    where s.code = 'MD.EQUALITY'`;
  expect(skill, "MD.EQUALITY is a skill").toBeTruthy();
  expect(skill.taught, "equations with × and ÷ wait for an educator's word").toBe(false);
  await sql`update skill_set set taught = true where code = ${skill.code}`;
  try {
    for (const k of SHOWS) {
      let text = "";
      for (let n = 1; n <= 3; n++) {
        await page.goto(`/library?set=MD.EQUALITY&difficulty=${k.level}&fmt=${k.fmt}&page=${n}#questions`);
        const main = page.getByRole("main");
        await expect(main.getByText(k.kind, { exact: true }).first()).toBeVisible();
        text += await main.getByRole("table").last().innerText();
        if (!(await main.getByRole("link", { name: /^Next \d+ →$/ }).count())) break;
      }
      for (const shows of k.shows) expect(text, `${k.level} ${k.fmt}`).toMatch(shows);
      expect(text, `${k.level} ${k.fmt}: a code on the page`).not.toMatch(CODE);
    }
  } finally {
    await sql`update skill_set set taught = false where code = ${skill.code}`;
  }
});
