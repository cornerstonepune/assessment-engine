/**
 * Multiples, factors and divisibility (goals/md4c-multiples-and-factors.yaml). MD.MULTIPLES is taught when an educator
 * says its grade has been taught it — its topic's switch — and until then no screen shows it
 * (goals/v1-only-what-is-taught.yaml). Switched on here as an educator's word would switch it, the Question bank shows
 * every question as the child meets it: the multiples up to a limit, a multiple or not, divisible by 2, 5 and 10, all
 * the factors, the factor pairs, the common multiples below a limit and divisible by 3 from the sum of the digits, each
 * list's answer its numbers, and every mistake named in words, never a code. The switch is put back.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// what each level's questions of each kind show, across every page of them
const SHOWS: { level: string; fmt: string; kind: string; shows: RegExp[] }[] = [
  {
    level: "Easy",
    fmt: "multiples",
    kind: "multiples and factors",
    shows: [
      /Write the multiples of (\d+) up to \d+\. You may not need every space\.[\s\S]*?\1, \d+, \d+/,
      /Is \d+ a multiple of \d+\?/,
      /Is \d{3} divisible by 2, by 5 and by 10\?/,
    ],
  },
  {
    level: "Medium",
    fmt: "multiples",
    kind: "multiples and factors",
    shows: [/Write all the factors of \d+\.[\s\S]*?1, \d+/, /Write the factor pairs of \d+\.[\s\S]*?1 × \d+, \d+ × \d+/],
  },
  { level: "Medium", fmt: "odd_even", kind: "odd or even", shows: [/will \d+ × \d+ be odd or even\?/] },
  {
    level: "Hard",
    fmt: "multiples",
    kind: "multiples and factors",
    shows: [/Write the common multiples of \d+ and \d+ below \d+\./],
  },
  {
    level: "Advance",
    fmt: "multiples",
    kind: "multiples and factors",
    shows: [/Is \d{3} divisible by 3\?/, /\d \+ \d \+ \d = □/],
  },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every multiple and factor is on the Question bank as the child meets it", async ({ page }) => {
  const [skill] = await sql<{ code: string; taught: boolean }[]>`
    select s.code, s.taught from skill_set s
    where s.code = 'MD.MULTIPLES'`;
  expect(skill, "MD.MULTIPLES is a skill").toBeTruthy();
  expect(skill.taught, "multiples and factors wait for an educator's word").toBe(false);
  await sql`update skill_set set taught = true where code = ${skill.code}`;
  try {
    for (const k of SHOWS) {
      let text = "";
      for (let n = 1; n <= 3; n++) {
        await page.goto(`/library?set=MD.MULTIPLES&difficulty=${k.level}&fmt=${k.fmt}&page=${n}#questions`);
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
