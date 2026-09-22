/**
 * Step 2 — the Skill Map as outcomes (goals/s2-skill-map-outcomes.yaml).
 *
 * Nimish, 2026-09-21: "the outcome needs to be articulated as a skill, not like two-digit addition
 * up to 10", and of the list under the map, "what's the point of listing all these things? It's not
 * even properly linked". Every skill is led by what the child can do; every link goes somewhere.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

type Skill = { code: string; outcome: string; name: string; band: string; words: Record<string, { words: string }> };
const LEVELS = ["Easy", "Medium", "Hard", "Advance"];
// A code a teacher should never have to read: a skill set, a rung, a mistake.
const CODE = /\b([A-Z]{2,}\.[A-Z0-9_.]+|R\d{1,2}|X[12]|M_[A-Z0-9_]+)\b/;

const skills = () => sql<Skill[]>`
  select s.code, s.learning_objective as outcome, s.name, r.band, s.difficulty as words
  from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
  order by r.ladder_order nulls last, s.code`;

async function noSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, "page must not scroll sideways").toBeLessThanOrEqual(1);
}

test("the map lists every skill by grade, each led by what the child can do, and no list that goes nowhere", async ({ page }) => {
  const all = await skills();
  await page.goto("/");
  for (const grade of ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Reasoning · Grade 2 and up"]) {
    await expect(page.getByRole("heading", { name: grade, exact: true })).toBeVisible();
  }
  for (const s of all) {
    await expect(page.getByRole("link", { name: s.outcome, exact: true })).toHaveAttribute("href", `/skill-sets/${s.code}`);
  }
  await expect(page.getByText("Registry skills")).toHaveCount(0);
  const tables = await page.getByRole("main").getByRole("table").allInnerTexts();
  expect(tables.join("\n")).not.toMatch(CODE);
});

test("every link on the Skill Map opens", async ({ page }) => {
  await page.goto("/");
  // The page arrives as its loading screen and the map streams in after; read the map, not the screen.
  await expect(page.getByRole("heading", { name: "Grade 1", exact: true })).toBeVisible();
  const hrefs = await page.getByRole("main").locator("a[href]").evaluateAll((as) => [
    ...new Set(as.map((a) => (a as HTMLAnchorElement).getAttribute("href")!.split("#")[0])),
  ]);
  expect(hrefs.length).toBeGreaterThan(17);
  for (const href of hrefs) {
    const res = await page.request.get(href);
    expect(res.status(), href).toBe(200);
  }
});

test("every skill page shows each level in a sentence with a real question, its kinds, mistakes and worksheets", async ({ page }) => {
  for (const s of await skills()) {
    await page.goto(`/skill-sets/${s.code}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(s.outcome);
    for (const d of LEVELS) {
      const card = page.getByRole("region", { name: d, exact: true });
      await expect(card.getByRole("heading", { name: d })).toBeVisible();
      await expect(card).toContainText(s.words[d].words);
      await expect(card.getByText("For example")).toBeVisible();
    }
    await expect(page.getByRole("table", { name: "Kinds of question" }).locator("tbody tr").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Mistakes it watches for" })).toBeVisible();
    await expect(page.locator("#worksheets")).toBeVisible();
    // The lead of the page — its heading and the four levels — never shows a code.
    const lead = [await page.getByRole("heading", { level: 1 }).innerText()];
    for (const d of LEVELS) lead.push(await page.getByRole("region", { name: d, exact: true }).locator("h3, p").first().innerText());
    expect(lead.join(" "), s.code).not.toMatch(CODE);
  }
});

test("changing a skill's words saves them and sends the skill back for approval", async ({ page }) => {
  const [before] = await sql`select name, learning_objective, difficulty, status, ratified_by from skill_set where code = 'ADD.2D.REG'`;
  const easy = "A 2-digit number plus a 1-digit number, one regroup in the ones, total under 100 (edited by a test).";
  try {
    await page.goto("/skill-sets/ADD.2D.REG/edit");
    await page.getByLabel("Easy").fill(easy);
    await page.getByRole("button", { name: "Save the words" }).click();
    await expect(page.getByRole("status")).toContainText("Saved");
    const [after] = await sql<{ status: string; difficulty: Record<string, { words: string; check: unknown }> }[]>`
      select status, difficulty from skill_set where code = 'ADD.2D.REG'`;
    expect(after.difficulty.Easy.words).toBe(easy);
    expect(after.difficulty.Easy.check).toEqual(before.difficulty.Easy.check);
    expect(after.status).toBe("draft");

    await page.getByRole("button", { name: "Approve as written" }).click();
    await expect(page.getByRole("status")).toContainText("Approved as written");
    const [approved] = await sql<{ status: string; ratified_by: string }[]>`
      select status, ratified_by from skill_set where code = 'ADD.2D.REG'`;
    expect(approved).toEqual({ status: "ratified", ratified_by: "End-to-end test" });
  } finally {
    // Two statements: putting the words back is itself a content change, which withdraws approval.
    await sql`update skill_set set name = ${before.name}, learning_objective = ${before.learning_objective},
              difficulty = ${sql.json(before.difficulty)} where code = 'ADD.2D.REG'`;
    await sql`update skill_set set status = ${before.status}, ratified_by = ${before.ratified_by} where code = 'ADD.2D.REG'`;
  }
});

test("every waiting skill is approved from one page, in the approver's name", async ({ page }) => {
  const before = await sql<{ code: string; status: string; ratified_by: string | null }[]>`
    select code, status, ratified_by from skill_set order by code`;
  const [table] = await sql<{ value: unknown }[]>`select value from config where key = 'skills.charges_by_kind.approved'`;
  try {
    await sql`update config set value = '{}'::jsonb where key = 'skills.charges_by_kind.approved'`;
    await sql`update skill_set set status = 'ratified', ratified_by = 'someone earlier'`;
    await sql`update skill_set set status = 'draft', ratified_by = null where code in ('ADD.1D.WITHIN10', 'MUL.1D')`;
    await page.goto("/");
    await page.getByRole("link", { name: "Read and approve →" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Approve the skills");
    // the table of what a mistake charges waits beside them (step 8b) and is approved with the same press
    await expect(page.getByRole("heading", { name: "What a wrong answer counts against" })).toBeVisible();
    await page
      .getByRole("button", { name: "Approve all 2 skills and what a wrong answer counts against as written, as End-to-end test" })
      .click();
    await expect(page.getByRole("status")).toContainText("Approved 2 as written");
    const [approved] = await sql<{ by: string; same: boolean }[]>`
      select a.value ->> 'by' as by, (a.value -> 'table') = t.value as same
      from config a, config t where a.key = 'skills.charges_by_kind.approved' and t.key = 'skills.charges_by_kind'`;
    expect(approved).toEqual({ by: "End-to-end test", same: true });
    const rows = await sql<{ code: string; ratified_by: string }[]>`
      select code, ratified_by from skill_set where code in ('ADD.1D.WITHIN10', 'MUL.1D') and status = 'ratified' order by code`;
    expect(rows).toEqual([
      { code: "ADD.1D.WITHIN10", ratified_by: "End-to-end test" },
      { code: "MUL.1D", ratified_by: "End-to-end test" },
    ]);
  } finally {
    for (const b of before) {
      await sql`update skill_set set status = ${b.status}, ratified_by = ${b.ratified_by} where code = ${b.code}`;
    }
    await sql`update config set value = ${sql.json((table?.value ?? {}) as never)} where key = 'skills.charges_by_kind.approved'`;
  }
});

test("the map and a skill page fit a phone", async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 860 });
  for (const path of ["/", "/skill-sets/SUB.2D.EXCH", "/skill-sets/approve", "/skill-sets/SUB.2D.EXCH/edit"]) {
    await page.goto(path, { waitUntil: "networkidle" });
    await noSidewaysScroll(page);
  }
});
