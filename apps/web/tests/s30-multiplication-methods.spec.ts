/**
 * Multiplication's written methods (goals/md2d2-multiplication-methods.yaml). MUL.2D1D, MUL.3D1D and MUL.2D2D are
 * taught when an educator says their grade has been taught them — their topic's switch — and until then no screen shows
 * them (goals/v1-only-what-is-taught.yaml). Switched on here as an educator's word would switch it, the Question bank
 * shows each written method as the child meets it, a blank for every step: partitioning part by part, a grid with a
 * blank in every cell, expanded columns a row for each product, a lattice a cell for each pair of digits — named in
 * words, never a code. The switch is put back after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// the kind, the skill set it is printed for, its name in words, what its question shows, and its drawing's label
const KINDS: { fmt: string; set: string; label: string; shows: RegExp; drawn?: RegExp }[] = [
  { fmt: "break_apart", set: "MUL.2D1D", label: "tens, then ones", shows: /\d+ × \d+ = ___[\s\S]*\d+ × \d+ = ___/ },
  { fmt: "grid_method", set: "MUL.2D2D", label: "grid method", shows: /= ___/, drawn: /^grid for \d+ × \d+$/ },
  { fmt: "expanded_columns", set: "MUL.3D1D", label: "expanded columns", shows: /\d+ × \d+ ___[\s\S]*\d+ × \d+ ___/ },
  { fmt: "lattice", set: "MUL.2D2D", label: "lattice", shows: /= ___/, drawn: /^lattice for \d+ × \d+$/ },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every written method is on the Question bank, a blank for each step", async ({ page }) => {
  const [topic] = await sql<{ code: string; taught: boolean }[]>`
    select t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code = 'MUL.2D1D'`;
  expect(topic.taught, "multiplication in columns waits for an educator's word").toBe(false);
  await sql`update topic set taught = true where code = ${topic.code}`;
  try {
    for (const k of KINDS) {
      await page.goto(`/library?set=${k.set}&fmt=${k.fmt}#questions`);
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
