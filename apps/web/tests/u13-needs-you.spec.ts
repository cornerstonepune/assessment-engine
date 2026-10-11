/**
 * NY1 — what waits on a person (goals/ny1-needs-you.yaml). Nimish, 2026-10-10: "I'm not even now able to figure out
 * what all papers I need to validate or for Achal to validate … I'm not seeing any of the multiplication, division".
 * Today lists every one of those things under the tab where it is done, shown to everyone signed in — the school's two
 * educators are its only layer (goals/ui1-menu-and-today.yaml); Curriculum switches a topic on in a person's name; a
 * skill is approved before its topic is on; a question the engine drafted for Achal is answered on the site. Every
 * change is put back after.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

test.afterAll(async () => {
  await sql.end();
});

/** Each kind of thing that waits, by the tab where Today lists it (goals/ui1-menu-and-today.yaml). */
const UNDER: Record<string, string> = {
  "Answers to check": "Assessments",
  "Papers to sign off": "Assessments",
  "Home assessments to approve": "Assessments",
  "Class papers to approve": "Assessments",
  "Skills to approve": "Curriculum",
  "Questions the engine drafted for you": "Curriculum",
  "Topics not taught yet": "Curriculum",
};

/** The number a Today line shows, or 0 when nothing of its kind waits and the line is left out. */
async function count(page: Page, line: string): Promise<number> {
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");
  const c = page.getByRole("region", { name: line, exact: true });
  if (!(await c.count())) return 0;
  return Number((await c.getByTestId("count").innerText()).replace(/\D/g, ""));
}

test("Today lists what waits on a person, under the tab where it is done, hidden from no one", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");
  // the school's two educators are its only layer: no line is filed under someone else's name
  await expect(page.getByText(/For others|For you|No one on the staff list/)).toHaveCount(0);
  for (const [line, tab] of Object.entries(UNDER)) {
    const it = page.getByRole("region", { name: line, exact: true });
    if (await it.count()) await expect(page.getByRole("region", { name: tab, exact: true }).getByRole("region", { name: line, exact: true }), line).toBeVisible();
  }
  // the topics no one has switched on yet, as Curriculum lists them, and one click to it
  const [{ off }] = await sql<{ off: number }[]>`select count(*)::int as off from topic where not taught`;
  expect(await count(page, "Topics not taught yet")).toBe(off);
  // every question the engine drafted, still waiting, whoever it was drafted for
  const [{ open }] = await sql<{ open: number }[]>`select count(*)::int as open from ask where answer is null`;
  expect(open, "the engine has drafted questions to answer").toBeGreaterThan(0);
  expect(await count(page, "Questions the engine drafted for you")).toBe(open);
  await page.getByRole("region", { name: "Topics not taught yet", exact: true }).getByRole("link").first().click();
  await expect(page.getByRole("region", { name: "Not taught yet", exact: true })).toBeVisible();
});

test("an educator switches a topic on, in their name, and its skills are on Curriculum and the Question bank", async ({ page }) => {
  const [topic] = await sql<{ name: string; taught: boolean }[]>`select name, taught from topic where code = 'DIVCOL'`;
  expect(topic.taught, "division by a 1-digit number waits for an educator's word").toBe(false);
  try {
    await page.goto("/");
    const off = page.getByRole("region", { name: "Not taught yet", exact: true });
    const row = off.getByRole("listitem").filter({ hasText: topic.name });
    await expect(row).toContainText("2-digit ÷ 1-digit");
    await expect(row).toContainText("3-digit ÷ 1-digit");
    await row.getByRole("button", { name: `Switch on, as ${TEST_STAFF.name}` }).click();
    await expect(page.getByRole("region", { name: "Not taught yet", exact: true })).not.toContainText(topic.name);
    const [now] = await sql<{ taught: boolean; taught_by: string | null }[]>`select taught, taught_by from topic where code = 'DIVCOL'`;
    expect(now).toEqual({ taught: true, taught_by: TEST_STAFF.name });
    // its skills are taught now: on the Question bank, with their questions
    await page.goto("/library?set=DIV.2D1D");
    await expect(page.getByRole("main")).toContainText("2-digit ÷ 1-digit");
    // and switched off again, in a person's name, it is off
    await page.goto("/");
    const on = page.getByRole("region", { name: "Taught in this school", exact: true });
    await on.locator("summary").click(); // switching a taught topic off is folded away from a stray click
    await on.getByRole("listitem").filter({ hasText: topic.name }).getByRole("button", { name: `Switch off, as ${TEST_STAFF.name}` }).click();
    await expect(page.getByRole("region", { name: "Not taught yet", exact: true })).toContainText(topic.name);
  } finally {
    await sql`update topic set taught = false, taught_by = null, taught_at = null where code = 'DIVCOL'`;
  }
});

test("a skill is approved before its topic is switched on", async ({ page }) => {
  const [before] = await sql<{ status: string; ratified_by: string | null }[]>`
    select status, ratified_by from skill_set where code = 'DIV.2D1D'`;
  try {
    await sql`update skill_set set status = 'draft', ratified_by = null where code = 'DIV.2D1D'`;
    await page.goto("/skill-sets/approve");
    const panel = page.getByRole("region", { name: "2-digit ÷ 1-digit", exact: true });
    await expect(panel).toContainText("Not taught yet");
    const waiting = await page.locator('input[name="code"]').count();
    await page.goto("/today");
    expect(await count(page, "Skills to approve")).toBe(waiting);
    // approved from its own page, as written, in the approver's name
    await page.goto("/skill-sets/DIV.2D1D");
    await expect(page.getByRole("main")).toContainText("Not taught yet");
    await page.getByRole("button", { name: /Approve as written/ }).click();
    await expect(page.getByRole("main")).toContainText(/Approved/);
    const [after] = await sql<{ status: string; ratified_by: string | null }[]>`
      select status, ratified_by from skill_set where code = 'DIV.2D1D'`;
    expect(after).toEqual({ status: "ratified", ratified_by: TEST_STAFF.name });
  } finally {
    await sql`update skill_set set status = ${before.status}, ratified_by = ${before.ratified_by} where code = 'DIV.2D1D'`;
  }
});

test("a question drafted for Achal is agreed or corrected on the site, in the name of who answers", async ({ page }) => {
  const asked = await sql<{ code: string; question: string }[]>`
    select code, question from ask where code in ('MD.A2', 'MD.A3') and answer is null order by code`;
  expect(asked.map((a) => a.code)).toEqual(["MD.A2", "MD.A3"]);
  const [{ n: before }] = await sql<{ n: number }[]>`select count(*)::int as n from ask where answer is null`;
  try {
    await page.goto("/asks");
    const a2 = page.getByRole("region", { name: asked[0].question, exact: true });
    await a2.getByRole("button", { name: `Agree as drafted, as ${TEST_STAFF.name}` }).click();
    const a3 = page.getByRole("region", { name: asked[1].question, exact: true });
    await a3.getByLabel("What it should say").fill("A remainder is written in words first, then with r from Grade 3");
    await a3.getByRole("button", { name: `Correct it, as ${TEST_STAFF.name}` }).click();
    const answered = page.getByRole("region", { name: "Answered", exact: true });
    await expect(answered).toContainText(asked[0].question);
    await expect(answered).toContainText("A remainder is written in words first, then with r from Grade 3");
    const rows = await sql<{ code: string; answer: string; correction: string | null; answered_by: string }[]>`
      select code, answer, correction, answered_by from ask where code in ('MD.A2', 'MD.A3') order by code`;
    expect(rows).toEqual([
      { code: "MD.A2", answer: "agreed", correction: null, answered_by: TEST_STAFF.name },
      { code: "MD.A3", answer: "corrected", correction: "A remainder is written in words first, then with r from Grade 3", answered_by: TEST_STAFF.name },
    ]);
    await page.goto("/today");
    expect(await count(page, "Questions the engine drafted for you")).toBe(before - 2);
  } finally {
    await sql`update ask set answer = null, correction = null, answered_by = null, answered_at = null where code in ('MD.A2', 'MD.A3')`;
  }
});
