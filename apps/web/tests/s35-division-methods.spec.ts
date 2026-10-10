/**
 * Division's written methods (goals/md3d-division-methods.yaml). DIV.2D1D and DIV.3D1D are taught when an educator says
 * their grade has been taught them — their topic's switch — and until then no screen shows them
 * (goals/v1-only-what-is-taught.yaml). Switched on here as an educator's word would switch it, the Question bank shows
 * each written division as the child meets it, a blank for every step: partitioning part by part, chunking a
 * take-away for each place, short division the division layout with a small blank where each exchange is written,
 * long division a row for every product and every number left — named in words, never a code. The switch is put back.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

// the kind, the skill set it is printed for, its name in words, what its question shows, and its drawing's label
const KINDS: { fmt: string; set: string; label: string; shows: RegExp; drawn?: RegExp }[] = [
  { fmt: "partitioning", set: "DIV.2D1D", label: "partitioning", shows: /\d+ ÷ \d+ = ___[\s\S]*\d+ ÷ \d+ = ___/ },
  { fmt: "chunking", set: "DIV.2D1D", label: "chunking", shows: /= ___/, drawn: /^\d+ ÷ \d+ by chunking$/ },
  { fmt: "column_grid", set: "DIV.3D1D", label: "column sum", shows: /\d/, drawn: /^\d+ ÷ \d+ in the division layout$/ },
  { fmt: "long_division", set: "DIV.3D1D", label: "long division", shows: /\d/, drawn: /^\d+ ÷ \d+ in long division$/ },
];
const CODE = /\bM_[A-Z_]+\b|\b[A-Z]{2,}\.[A-Z0-9_.]+\b/;

test.afterAll(async () => {
  await sql.end();
});

test("once taught, every written division is on the Question bank, a blank for each step", async ({ page }) => {
  const [topic] = await sql<{ code: string; taught: boolean }[]>`
    select t.code, t.taught from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    where s.code = 'DIV.2D1D'`;
  expect(topic.taught, "division by a 1-digit number waits for an educator's word").toBe(false);
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
