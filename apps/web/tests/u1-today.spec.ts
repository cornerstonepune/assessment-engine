/**
 * U1 — Today and the menu (goals/u1-today.yaml).
 *
 * Today is the educators' inbox: everything waiting on a person, each with the count the page it opens shows and one
 * click to act, listed under the tab where it is done (goals/ui1-menu-and-today.yaml). The class papers and the child whose work suggests a next paper are the test's own, made on the copy
 * and cleared afterwards; the rest is compared with whatever the copy holds.
 */
import { expect, type Page, test } from "@playwright/test";
import postgres from "postgres";
import { isoWeek } from "../lib/week";
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

/** The rows of one kind on What needs doing (Today's old address), and how many answers, papers or children they say. */
async function kind(page: Page, k: string): Promise<{ rows: number; n: number }> {
  await page.goto(`/today?kind=${k}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What needs doing");
  const many = await page.locator(`tr[data-kind=${k}] td[data-label="How many"]`).allInnerTexts();
  return { rows: many.length, n: many.reduce((t, m) => t + Number(m.replace(/\D/g, "")), 0) };
}

test.beforeAll(async () => {
  await clearUp();
  await testChild();
  await engine("/week/prescribe", { section: SECTION, week: WEEK, skill_set: "SUB.2D2D" });
  await engine("/week/assemble", { section: SECTION, week: WEEK });
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

test("the menu is the teacher's week, and says where they are", async ({ page }) => {
  await page.goto("/today");
  const menu = page.getByRole("navigation", { name: "Sections" });
  // five groups (goals/nav_teacher_scope_and_todo.yaml); the group's count of what waits follows its name
  await expect(menu.getByRole("link")).toHaveText([/^What needs doing/, /^Teaching/, /^Assessments/, /^Results/, /^Setup/]);
  for (const [label, heading] of [
    ["Setup", "Curriculum"],
    ["Assessments", "Assessments"],
    ["Results", "Class results"],
    ["Teaching", "Teaching"],
    ["What needs doing", "What needs doing"],
  ]) {
    await menu.getByRole("link", { name: new RegExp(`^${label}\\b`) }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(menu.getByRole("link", { name: new RegExp(`^${label}\\b`) })).toHaveAttribute("aria-current", "page");
  }
});

test("today lists everything waiting on a teacher, each with its count and one click to act", async ({ page }) => {
  await page.goto("/today?kind=classpaper");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What needs doing");

  // the class papers the engine proposed for the test's class wait for a teacher before they print
  const pack = page.locator("tr[data-kind=classpaper]").filter({ hasText: new RegExp(`${SECTION} · class practice · `) });
  await expect(pack).toHaveCount(1);
  await pack.getByRole("link").click();
  await expect(page).toHaveURL(new RegExp(`/papers/approve\\?section=${SECTION}&week=${WEEK}&kind=practice`));

  // a child whose checked work gives the engine a home paper to propose — red, amber or green on any skill —
  // with no home paper approved this week: a row for each class, counting its children
  const [{ n }] = await sql<{ n: number }[]>`
    select count(distinct s.child_id)::int as n from child_skill_state s join child c on c.id = s.child_id
    where c.active and s.state in ('patterned_error', 'emerging', 'practising', 'secure', 'stretch_ready')
      and not exists (select 1 from sheet_instance si where si.child_id = s.child_id and si.kind = 'focus'
                      and si.week = ${isoWeek()})`;
  const home = await kind(page, "home");
  expect(home.n).toBe(n);
  if (n) {
    await page.locator("tr[data-kind=home]").first().getByRole("link").click();
    await expect(page).toHaveURL(/\/make\/[^/]+$/);
  }

  // the skills that wait for an approval: one row each, every skill waiting, taught or not (goals/ny1-needs-you.yaml)
  const [{ drafts }] = await sql<{ drafts: number }[]>`select count(*)::int as drafts from skill s where s.status <> 'ratified'`;
  await page.goto("/today?kind=skill");
  const counted = (await page.locator("details[data-topic] > summary .fact").allInnerTexts()).reduce((t, x) => t + Number(x.replace(/\D/g, "")), 0);
  expect(counted).toBe(drafts);
  if (drafts > 0) {
    await page.locator("tr[data-kind=skill]").first().getByRole("link").click();
    await expect(page).toHaveURL(/\/skill-sets\/[A-Z0-9_.]+$/);
  }
});

test("what has nothing waiting says so, and each count is the page's own", async ({ page }) => {
  const check = await kind(page, "check");
  await page.goto("/capture/check");
  await expect(page.getByText(`${check.n} ${check.n === 1 ? "answer" : "answers"} left to check`)).toBeVisible();

  const sign = await kind(page, "signoff");
  await page.goto("/capture");
  await expect(page.getByRole("region", { name: "Answers to check" }).getByTestId("to-sign")).toHaveText(String(sign.rows));

  // what has nothing waiting is not listed: a kind with no row says so, and every number shown is above zero
  await page.goto("/today");
  for (const n of await page.locator("td[data-label=\"How many\"]").allInnerTexts()) if (/\d/.test(n)) expect(Number(n.replace(/\D/g, ""))).toBeGreaterThan(0);
  await page.goto("/today?kind=empty");
  if (!(await page.locator("tr[data-kind=empty]").count())) await expect(page.getByText(/Nothing waits on you/)).toBeVisible();
});

test("Today has the one filter row: a place and what waits narrow its lines (goals/uxn10-today.yaml)", async ({ page }) => {
  await page.goto("/today");
  await expect(page.locator("[data-filterbar]")).toBeVisible();
  await page.goto("/today?kind=skill");
  await expect(page.locator("[data-active-filters]")).toContainText("What: Approve a skill");
  await expect(page.locator("tr[data-kind]:not([data-kind=skill])")).toHaveCount(0);
  await page.goto("/today?subject=NUM");
  await expect(page.locator("[data-active-filters]")).toContainText("Subject: Maths");
  for (const where of await page.locator("td[data-label=Where]").allInnerTexts()) expect(where).not.toMatch(/^English/);
});
