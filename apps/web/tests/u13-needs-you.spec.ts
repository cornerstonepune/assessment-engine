/**
 * NY1 — what waits on a person, and who it is for (goals/ny1-needs-you.yaml). Nimish, 2026-10-10: "I'm not even now
 * able to figure out what all papers I need to validate or for Achal to validate … I'm not seeing any of the
 * multiplication, division". Today names whose each thing is (`people.decides`, the staff list's roles), the
 * signed-in person's first; Curriculum switches a topic on in a person's name; a skill is approved before its topic is
 * on; a question the engine drafted for Achal is answered on the site. Every change is put back after.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

test.afterAll(async () => {
  await sql.end();
});

type Staff = { name: string; role: string };
/** Each card on Today, by the kind of waiting `people.decides` names. */
const CARDS: Record<string, string> = {
  "Answers to check": "answers",
  "Papers to sign off": "papers",
  "Home assessments to approve": "home_papers",
  "Class papers to approve": "class_papers",
  "Skills to approve": "skills",
  "Topics not taught yet": "topics",
};
const ROLE_WORDS: Record<string, string> = { coordinator: "a coordinator", educator: "an educator", specialist: "a specialist" };

/** The number a Today card shows, or 0 when it says nothing is waiting. */
async function count(page: Page, card: string): Promise<number> {
  const c = page.getByRole("region", { name: card, exact: true });
  await expect(c).toBeVisible();
  if (await c.getByText("Nothing waiting").isVisible()) return 0;
  return Number((await c.getByTestId("count").innerText()).replace(/\D/g, ""));
}

/** Who a card says it is for, worked from the rows: "For you", the names of those whose role it is, or no one yet. */
function whoFor(roles: string[], staff: Staff[]): string {
  if (roles.includes(TEST_STAFF.role)) return "For you";
  const names = staff.filter((s) => roles.includes(s.role)).map((s) => s.name);
  return names.length ? `For ${names.join(", ")}` : `No one on the staff list is ${roles.map((r) => ROLE_WORDS[r]).join(" or ")} yet`;
}

test("Today lists what waits on a person, yours first, each saying who it is for", async ({ page }) => {
  const [{ value: decides }] = await sql<{ value: Record<string, string[]> }[]>`select value from config where key = 'people.decides'`;
  const [{ value: staff }] = await sql<{ value: Staff[] }[]>`select value from config where key = 'app.staff'`;
  await page.goto("/today");
  const mine = page.getByRole("region", { name: "For you", exact: true });
  const others = page.getByRole("region", { name: "For others", exact: true });
  for (const [title, kind] of Object.entries(CARDS)) {
    const roles = decides[kind];
    const card = (roles.includes(TEST_STAFF.role) ? mine : others).getByRole("region", { name: title, exact: true });
    await expect(card, title).toBeVisible();
    await expect(card, title).toContainText(whoFor(roles, staff));
  }
  // the topics no one has switched on yet, as Curriculum lists them, and one click to it
  const [{ off }] = await sql<{ off: number }[]>`select count(*)::int as off from topic where not taught`;
  expect(await count(page, "Topics not taught yet")).toBe(off);
  // each person's questions to answer, in their own card: an educator's are Achal's, a teacher's
  const open = await sql<{ for_role: string; n: number }[]>`
    select for_role, count(*)::int as n from ask where answer is null group by for_role order by for_role`;
  expect(open.length, "the engine has drafted questions to answer").toBeGreaterThan(0);
  for (const { for_role, n } of open) {
    const title = `Questions for ${ROLE_WORDS[for_role]}`;
    expect(await count(page, title)).toBe(n);
    await expect(page.getByRole("region", { name: title, exact: true })).toContainText(whoFor([for_role], staff));
  }
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
  const [{ n: before }] = await sql<{ n: number }[]>`select count(*)::int as n from ask where answer is null and for_role = 'educator'`;
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
    expect(await count(page, "Questions for an educator")).toBe(before - 2);
  } finally {
    await sql`update ask set answer = null, correction = null, answered_by = null, answered_at = null where code in ('MD.A2', 'MD.A3')`;
  }
});
