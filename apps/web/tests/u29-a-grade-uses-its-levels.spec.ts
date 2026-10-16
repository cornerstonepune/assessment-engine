/**
 * U29 — a grade uses its own levels and those below (goals/f1e-the-grade-plan.yaml, ADR 0073 D2). Nimish, 2026-10-14:
 * "whenever a grade two teacher is creating the assessments for that topic, it's only easy and medium that should
 * come." Each level has a grade, set on the skill's page. Since L7 (ADR 0081, Nimish, 2026-10-16: the educator's choice
 * decides) Make papers offers every level, a level of a higher grade said so, and a skill's first level of the
 * class's own grade chosen for it. 2-digit + 1-digit is Grade 2's and its Easy Grade 1's.
 *
 * The classes are the test's own (tests/rows.ts), made once and kept.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => {
  await sql.end();
});

test("make papers offers a class its own grade's levels first, a higher grade's said so", async ({ page }) => {
  await aClass(sql, "U29-G1", "G1", ["Ira", "Jai"]);
  await aClass(sql, "U29-G2", "G2", ["Kavya", "Laksh"]);
  const offered = async (cls: string) => {
    await page.goto(`/papers/make?class=${cls}`);
    await page.getByLabel("Topic 1").selectOption("ADDSUB");
    await page.getByLabel("Skill 1").selectOption("ADD.2D1D");
    const options = (await page.getByLabel("Level 1").locator("option").allTextContents()).slice(1);
    return { levels: options.map((o) => o.replace(/ · \d+ questions/, "")), chosen: await page.getByLabel("Level 1").inputValue() };
  };
  expect(await offered("U29-G1"), "Grade 1's own level is chosen; the others say they are Grade 2's").toEqual({
    levels: ["Easy", "Medium · Grade 2", "Hard · Grade 2", "Advance · Grade 2"],
    chosen: "Easy",
  });
  expect(await offered("U29-G2"), "Grade 2 uses every level").toEqual({ levels: ["Easy", "Medium", "Hard", "Advance"], chosen: "Medium" });
});
