/**
 * Multiplication's first models (goals/md2d1-multiplication-models.yaml). What an educator sees on the Question bank:
 * skip counting as its steps before a blank, an array as rows of dots, equal jumps from 0 on a number line, and a cell
 * of the multiplication square among its neighbours, each as the child meets it, named in words, never a code.
 */
import { expect, test } from "@playwright/test";

// the kind, its name in words, what its questions show, and the label of its drawing (components/pictures.tsx)
const KINDS: { fmt: string; label: string; shows: RegExp; drawn?: RegExp }[] = [
  { fmt: "skip_counting", label: "skip counting", shows: /\b\d+, \d+, \d+, (\d+, )*___/ },
  { fmt: "equal_groups", label: "equal groups", shows: /rows/, drawn: /^\d+ rows of \d+$/ },
  { fmt: "number_line_jumps", label: "number line", shows: /\d+ jumps of \d+ from 0/ },
  { fmt: "multiplication_square", label: "multiplication square", shows: /\d+/, drawn: /^part of the multiplication square$/ },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test("multiplication's models are on the Question bank, drawn as the child meets them", async ({ page }) => {
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
});
