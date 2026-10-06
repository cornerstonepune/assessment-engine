/**
 * Grade 1 as its educator taught it to September (goals/g1-taught-till-september.yaml). What an educator sees: the
 * two kinds of question Grade 1 needed and the bank did not have are on the Question bank, drawn as the child meets
 * them (a tally's lines, equal groups' rings of dots or the same number added again), named in words, never a code.
 */
import { expect, test } from "@playwright/test";

// the kind, its name in words, words its questions carry, and the label of its drawing (components/pictures.tsx)
const KINDS: [string, string, RegExp, RegExp][] = [
  ["tally", "tally marks", /does the tally show\?|altogether\?|How many more/, /^a tally of \d+$/],
  ["equal_groups", "equal groups", /in all\?|\d \+ \d/, /^\d groups of \d$/],
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test("Grade 1's tally marks and equal groups are on the Question bank, drawn as the child meets them", async ({
  page,
}) => {
  for (const [fmt, label, words, drawn] of KINDS) {
    await page.goto(`/library?fmt=${fmt}#questions`);
    const main = page.getByRole("main");
    await expect(main.getByText(label, { exact: true }).first()).toBeVisible();
    const questions = main.getByRole("table").last();
    const text = await questions.innerText();
    expect(text, fmt).toMatch(words);
    expect(text, `${fmt}: a code on the page`).not.toMatch(CODE);
    await expect(questions.getByLabel(drawn).first()).toBeVisible();
  }
});
