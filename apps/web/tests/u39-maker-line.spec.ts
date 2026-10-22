/**
 * U39 — each line of Make papers is a topic, its skill, a level and how many (goals/l7-a-line-is-topic-skill-level-number.yaml,
 * ADR 0081). Achal, through Nimish, 2026-10-16: "Didn't we add two-digit by two-digit multiplication yesterday? … even
 * multiples and factors are not visible. … If I'm choosing a topic, it should only show the skills related to that
 * topic, right? Ideally, for an assessment, I should be able to create questions from multiple topics."
 *
 * A Grade 3 class of the test's own (tests/rows.ts). 2-digit × 2-digit is Grade 4 at every level; multiples are Grade 3
 * at Easy and Medium, Grade 4 at Hard and Advance; neither is taught in the school's rows.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "U39-G3";
test.afterAll(async () => {
  await sql.end();
});

const names = async (codes: string[]) =>
  Object.fromEntries((await sql<{ code: string; name: string }[]>`select code, name from skill where code = any(${codes})`).map((r) => [r.code, r.name]));

test("a line's skills are its topic's, and one paper takes lines from different topics", async ({ page }) => {
  await aClass(sql, CLASS, "G3", ["Ira", "Jai"]);
  const mul = await sql<{ code: string }[]>`select code from skill where topic_code = 'MUL' and difficulty <> '{}'::jsonb`;
  const name = await names(["MUL.2D2D", "MD.MULTIPLES"]);
  await page.goto(`/papers/make?class=${CLASS}&kind=assessment&way=same`);
  const form = page.getByRole("form", { name: "Choose the papers" });

  await form.getByLabel("Topic 1").selectOption("MUL");
  const offered = await form.getByLabel("Skill 1").locator("option").evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value).filter(Boolean));
  expect(offered.sort(), "the skills of the line's topic, and only those").toEqual(mul.map((r) => r.code).sort());
  await form.getByLabel("Skill 1").selectOption("MUL.2D2D");
  await form.getByLabel("Level 1").selectOption("Medium");
  await form.getByLabel("Questions 1").fill("3");

  await form.getByLabel("Topic 2").selectOption("FACTORS");
  await form.getByLabel("Skill 2").selectOption("MD.MULTIPLES");
  await form.getByLabel("Level 2").selectOption("Hard");
  await form.getByLabel("Questions 2").fill("3");
  await form.getByRole("button", { name: "See the papers" }).click();

  const papers = page.getByRole("region", { name: "The papers" });
  await expect(papers.getByRole("list", { name: `${name["MUL.2D2D"]} · Medium` }).getByRole("listitem")).toHaveCount(3);
  await expect(papers.getByRole("list", { name: `${name["MD.MULTIPLES"]} · Hard` }).getByRole("listitem")).toHaveCount(3);
  await expect(papers.getByRole("button", { name: "Make and approve 2 class assessment papers" })).toBeEnabled();
  // the lines come back as chosen, each under its own topic
  await expect(form.getByLabel("Topic 2")).toHaveValue("FACTORS");
  await expect(form.getByLabel("Skill 2")).toHaveValue("MD.MULTIPLES");
});

test("every skill of a topic is offered, a higher grade and an untaught skill said so", async ({ page }) => {
  await aClass(sql, CLASS, "G3", ["Ira", "Jai"]);
  const name = await names(["MUL.2D2D", "MUL.3D1D", "MD.MULTIPLES"]);
  await page.goto(`/papers/make?class=${CLASS}&kind=assessment&way=same`);
  const form = page.getByRole("form", { name: "Choose the papers" });

  await form.getByLabel("Topic 1").selectOption("MUL");
  const skills = (await form.getByLabel("Skill 1").locator("option").allTextContents()).slice(1);
  const twoByTwo = skills.find((o) => o.startsWith(name["MUL.2D2D"]));
  expect(twoByTwo, "2-digit × 2-digit is offered to Grade 3").toBe(`${name["MUL.2D2D"]} · Grade 4 · not taught yet`);
  // the class's own grade first: the two skills that are Grade 4 at every level come last
  expect(skills.slice(-2).map((o) => o.split(" · ")[0]).sort()).toEqual([name["MUL.2D2D"], name["MUL.3D1D"]].sort());

  await form.getByLabel("Topic 1").selectOption("FACTORS");
  await form.getByLabel("Skill 1").selectOption("MD.MULTIPLES");
  const levels = (await form.getByLabel("Level 1").locator("option").allTextContents()).slice(1);
  expect(levels.map((o) => o.replace(/ · \d+ questions/, ""))).toEqual(["Easy", "Medium", "Hard · Grade 4", "Advance · Grade 4"]);
  await expect(form.getByLabel("Level 1"), "a skill's first level of the class's grade, Medium where it has one").toHaveValue("Medium");
});
