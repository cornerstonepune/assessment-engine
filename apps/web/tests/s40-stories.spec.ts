/**
 * Stories with × and ÷ (goals/md4d1-times-stories.yaml). MD.WORD is taught when an educator says its grade has been
 * taught it — its topic's switch — and until then no screen shows it (goals/v1-only-what-is-taught.yaml). Switched on
 * here as an educator's word would switch it, the Question bank shows every story as the child meets it: half as many,
 * times as many the smaller and how many times, the two-step stories, a number the story does not need and a price
 * list, each with its answer, and every mistake named in words, never a code. The switch is put back.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// what each level's stories of each kind show, across every page of them
const SHOWS: { level: string; fmt: string; kind: string; shows: RegExp[] }[] = [
  { level: "Medium", fmt: "word_1step", kind: "one-step word problem", shows: [/half as many/] },
  {
    level: "Hard",
    fmt: "word_1step",
    kind: "one-step word problem",
    shows: [/\d+ times as many as [A-Z][a-z]+\. How many/, /How many times as many/],
  },
  {
    level: "Advance",
    fmt: "word_2step",
    kind: "two-step word problem",
    shows: [/times as many/, /\d+ [a-z]+ (of|with) \d+/],
  },
  { level: "Advance", fmt: "word_1step", kind: "one-step word problem", shows: [/₹\d+/] },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every × and ÷ story is on the Question bank as the child meets it", async ({ page }) => {
  const [topic] = await sql<{ code: string; taught: boolean }[]>`
    select t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code = 'MD.WORD'`;
  expect(topic, "MD.WORD has a topic of its own").toBeTruthy();
  expect(topic.taught, "stories with × and ÷ wait for an educator's word").toBe(false);
  await sql`update topic set taught = true where code = ${topic.code}`;
  try {
    for (const k of SHOWS) {
      let text = "";
      for (let n = 1; n <= 4; n++) {
        await page.goto(`/library?set=MD.WORD&difficulty=${k.level}&fmt=${k.fmt}&page=${n}#questions`);
        const main = page.getByRole("main");
        await expect(main.getByText(k.kind, { exact: true }).first()).toBeVisible();
        text += await main.getByRole("table").last().innerText();
        if (!(await main.getByRole("link", { name: /^Next \d+ →$/ }).count())) break;
      }
      for (const shows of k.shows) expect(text, `${k.level} ${k.fmt}`).toMatch(shows);
      expect(text, `${k.level} ${k.fmt}: a code on the page`).not.toMatch(CODE);
    }
  } finally {
    await sql`update topic set taught = false where code = ${topic.code}`;
  }
});
