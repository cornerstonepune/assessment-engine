/**
 * U29 — a grade uses its own levels and those below (goals/f1e-the-grade-plan.yaml, ADR 0073 D2). Nimish, 2026-10-14:
 * "whenever a grade two teacher is creating the assessments for that topic, it's only easy and medium that should
 * come." Each level has a grade, set on the skill's page; Make papers offers a class only its grade's levels and those
 * of the grades below. 2-digit + 1-digit is Grade 2's and its Easy Grade 1's: Grade 1 is offered Easy alone, Grade 2
 * every level.
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

test("make papers offers a class only its grade's levels and those below", async ({ page }) => {
  await aClass(sql, "U29-G1", "G1", ["Ira", "Jai"]);
  await aClass(sql, "U29-G2", "G2", ["Kavya", "Laksh"]);
  const [{ name }] = await sql<{ name: string }[]>`select name from skill_set where code = 'ADD.2D1D'`;
  const offered = async (cls: string) => {
    await page.goto(`/papers/make?class=${cls}`);
    const options = await page.getByLabel("Skill and level 1").locator("option").allTextContents();
    return options.filter((o) => o.startsWith(`${name} · `)).map((o) => o.split(" · ")[1].split(" (")[0]);
  };
  expect(await offered("U29-G1"), "Grade 1 is offered Grade 1's level alone").toEqual(["Easy"]);
  expect((await offered("U29-G2")).sort(), "Grade 2 is offered every level").toEqual(["Advance", "Easy", "Hard", "Medium"]);
});
