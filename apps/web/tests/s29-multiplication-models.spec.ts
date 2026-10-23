/**
 * Multiplication's first models (goals/md2d1-multiplication-models.yaml). They are taught when an educator says Grade 2
 * has been taught them — their topic's switch — and until then no screen shows them (goals/v1-only-what-is-taught.yaml).
 * Switched on here as an educator's word would switch it, the Question bank shows each as the child meets it: skip
 * counting as its steps before a blank, an array as rows of dots, equal jumps from 0 on a number line, and a cell of
 * the multiplication square among its neighbours, named in words, never a code. The switch is put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aTaughtClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// the kind, its name in words, what its questions show, and the label of its drawing (components/pictures.tsx)
const KINDS: { fmt: string; label: string; shows: RegExp; drawn?: RegExp }[] = [
  { fmt: "skip_counting", label: "skip counting", shows: /\b\d+, \d+, (\d+, )*___/ },
  { fmt: "equal_groups", label: "equal groups", shows: /rows/, drawn: /^\d+ rows of \d+$/ },
  { fmt: "number_line_jumps", label: "number line", shows: /\d+ jumps of \d+ from 0/ },
  { fmt: "multiplication_square", label: "multiplication square", shows: /\d+/, drawn: /^part of the multiplication square$/ },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.beforeAll(async () => {
  await aTaughtClass(sql);
});

test.afterAll(async () => {
  await sql.end();
});

test("once taught, multiplication's models are on the Question bank, drawn as the child meets them", async ({ page }) => {
  const [skill] = await sql<{ code: string; taught: boolean }[]>`
    select s.code, s.taught from skill s
    where s.code = 'MUL.MODELS'`;
  expect(skill.taught, "multiplication's models wait for an educator's word").toBe(false);
  await sql`update skill set taught = true where code = ${skill.code}`;
  try {
    for (const k of KINDS) {
      await page.goto(`/library?set=MUL.MODELS&fmt=${k.fmt}#questions`);
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
    await sql`update skill set taught = false where code = ${skill.code}`;
  }
});
