/**
 * Division's first models (goals/md3c-division-models.yaml). They are taught when an educator says Grade 2 has been
 * taught them — their topic's switch — and until then no screen shows them (goals/v1-only-what-is-taught.yaml).
 * Switched on here as an educator's word would switch it, the Question bank shows each as the child meets it: dots to
 * share into rings or to ring in groups, an array read as in all ÷ rows = in each row, a number taken away again and
 * again to 0 printed whole, jumps back on a number line, and the stories, named in words, never a code. The switch is
 * put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// the kind, its name in words, what its questions show, and the labels of its drawings (components/pictures.tsx)
const KINDS: { fmt: string; label: string; shows: RegExp; drawn?: RegExp }[] = [
  {
    fmt: "equal_groups",
    label: "equal groups",
    shows: /in each ring|groups|in all ___ ÷ rows ___ = in each row ___/,
    drawn: /^\d+ dots to share into \d+ rings$|^\d+ dots to ring in groups$|^\d+ rows of \d+$/,
  },
  { fmt: "repeated_subtraction", label: "repeated subtraction", shows: /\d+ − \d+ − (\d+ − )*\d+ = 0/ },
  { fmt: "number_line_jumps", label: "number line", shows: /[Jj]ump back \d+ at a time/ },
  { fmt: "word_1step", label: "one-step word problem", shows: /\d+/ },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, division's models are on the Question bank, drawn as the child meets them", async ({ page }) => {
  const [topic] = await sql<{ code: string; taught: boolean }[]>`
    select t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code = 'DIV.GROUPS'`;
  expect(topic.taught, "division's models wait for an educator's word").toBe(false);
  await sql`update topic set taught = true where code = ${topic.code}`;
  try {
    for (const k of KINDS) {
      await page.goto(`/library?set=DIV.GROUPS&fmt=${k.fmt}#questions`);
      const main = page.getByRole("main");
      await expect(main.getByText(k.label, { exact: true }).first()).toBeVisible();
      const questions = main.getByRole("table").last();
      const text = await questions.innerText();
      expect(text, k.fmt).toMatch(k.shows);
      expect(text, `${k.fmt}: a code on the page`).not.toMatch(CODE);
      if (k.drawn) {
        const labels = await questions
          .locator("[aria-label]")
          .evaluateAll((els) => els.map((e) => e.getAttribute("aria-label") ?? ""));
        expect(labels.some((l) => k.drawn!.test(l)), `${k.fmt}: not drawn`).toBe(true);
      }
    }
  } finally {
    await sql`update topic set taught = false where code = ${topic.code}`;
  }
});
