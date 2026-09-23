/**
 * U1 — Today and the menu (goals/u1-today.yaml).
 *
 * Today is the teacher's inbox: everything waiting on a person, each with the count the page it opens shows and one
 * click to act. The class papers and the child whose work suggests a next paper are the test's own, made on the copy
 * and cleared afterwards; the rest is compared with whatever the copy holds.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";
import { ENGINE_PORT } from "../playwright.config";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U1-TEST";
const WEEK = "U1-TEST";

async function engine(path: string, body: object) {
  const r = await fetch(`http://127.0.0.1:${ENGINE_PORT}${path}`, {
    method: "POST",
    headers: {
      "X-Engine-Key": process.env.E2E_ENGINE_KEY!,
      "content-type": "application/json",
      "Idempotency-Key": `u1-${path}-${Date.now()}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json();
}

/** A Grade 2 child of the test's own whose checked answers show subtraction under half right. */
async function testChild(): Promise<string> {
  const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (had) return had.id;
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const [{ id }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G2') returning id`;
  await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, 'Today')`;
  for (const right of [false, false, false, false, true, true]) {
    await sql`
      insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at, confirmed_by)
      values (${tenant_id}, ${id}, 'NUM.OPS.02', 'R6', ${right}, 'item', now(), 'e2e')`;
  }
  await sql`select rebuild_child_skill_state(${id}::uuid)`;
  return id;
}

async function clearUp() {
  await sql`delete from item_exposure where week = ${WEEK}`;
  await sql`delete from prescription where week = ${WEEK}`;
  await sql`delete from sheet_instance where week = ${WEEK}`;
}

/** The number a Today card shows, or 0 when it says nothing is waiting. */
async function count(page: Page, card: string): Promise<number> {
  const c = page.getByRole("region", { name: card });
  await expect(c).toBeVisible();
  if (await c.getByText("Nothing waiting").isVisible()) return 0;
  return Number((await c.getByTestId("count").innerText()).replace(/\D/g, ""));
}

test.beforeAll(async () => {
  await clearUp();
  await testChild();
  await engine("/week/prescribe", { section: SECTION, week: WEEK, skill_set: "SUB.2D.EXCH" });
  await engine("/week/assemble", { section: SECTION, week: WEEK });
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

test("the menu is the teacher's week, and says where they are", async ({ page }) => {
  await page.goto("/today");
  const menu = page.getByRole("navigation", { name: "Sections" });
  await expect(menu.getByRole("link")).toHaveText([
    "Today",
    "Children",
    "Marking",
    "Papers",
    "Curriculum",
    "Question bank",
    "How it works",
  ]);
  for (const [label, heading] of [
    ["Children", "Children"],
    ["Marking", "Marking"],
    ["Papers", "Worksheets"],
    ["Curriculum", "Skill Map"],
    ["Question bank", "Question bank"],
    ["Today", "Today"],
  ]) {
    await menu.getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(menu.getByRole("link", { name: label, exact: true })).toHaveAttribute("aria-current", "page");
  }
});

test("today lists everything waiting on a teacher, each with its count and one click to act", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");

  // the class papers the engine proposed for the test's class wait for a teacher before they print
  const papers = page.getByRole("region", { name: "Class papers to approve" });
  const pack = papers.getByRole("link", { name: new RegExp(`${SECTION} · ${WEEK}`) });
  await expect(pack).toBeVisible();
  await pack.click();
  await expect(page).toHaveURL(new RegExp(`/worksheets\\?section=${SECTION}&week=${WEEK}&kind=practice`));

  // a child whose checked work shows a red or amber skill, with no next paper made this week
  await page.goto("/today");
  const [{ n }] = await sql<{ n: number }[]>`
    select count(distinct s.child_id)::int as n from child_skill_state s join child c on c.id = s.child_id
    where c.active and s.state in ('patterned_error', 'emerging', 'practising')
      and not exists (select 1 from sheet_instance si where si.child_id = s.child_id and si.kind = 'focus'
                      and si.created_at > date_trunc('week', now()))`;
  expect(await count(page, "Next papers to approve")).toBe(n);
  await page.getByRole("region", { name: "Next papers to approve" }).getByRole("link").first().click();
  await expect(page).toHaveURL(/\/growth/);

  // the skills that wait for an approval
  await page.goto("/today");
  const [{ drafts }] = await sql<{ drafts: number }[]>`select count(*)::int as drafts from skill_set where status <> 'ratified'`;
  expect(await count(page, "Skills to approve")).toBe(drafts);
  if (drafts > 0) {
    await page.getByRole("region", { name: "Skills to approve" }).getByRole("link").first().click();
    await expect(page).toHaveURL(/\/skill-sets\/approve/);
  }
});

test("what has nothing waiting says so, and each count is the page's own", async ({ page }) => {
  await page.goto("/today");
  const toCheck = await count(page, "Answers to check");
  await page.goto("/capture/check");
  await expect(page.getByText(`${toCheck} ${toCheck === 1 ? "answer" : "answers"} left to check`)).toBeVisible();

  await page.goto("/today");
  const toSign = await count(page, "Papers to sign off");
  await page.goto("/capture");
  await expect(page.getByText("papers to sign off").locator("..")).toContainText(String(toSign));

  // on a card with nothing waiting there is no number and no button, only the words
  await page.goto("/today");
  for (const card of ["Answers to check", "Papers to sign off", "Skills to approve"]) {
    const c = page.getByRole("region", { name: card });
    if ((await count(page, card)) === 0) {
      await expect(c.getByText("Nothing waiting")).toBeVisible();
      await expect(c.getByTestId("count")).toHaveCount(0);
    }
  }
});
