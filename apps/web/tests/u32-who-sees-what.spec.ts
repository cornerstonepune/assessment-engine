/**
 * U32 — who sees what (goals/ux1-who-sees-what.yaml, BUILD-ORDER "topics are operations, and every page is the
 * educator's own"). Nimish, 2026-10-15, on live's pages: "It should be teacher-specific and all of those things."
 *
 * An educator is shown only what is theirs: no decision the school gives to someone else, no other class's child by
 * name — not on the page and not read for them, since every name read is logged — and the menu counting what Today
 * lists. The coordinator is shown everything, as before. That a decision is refused on the server whatever a page
 * shows is u27's; this is what the pages offer.
 *
 * Two Grade 2 classes of the test's own (tests/rows.ts), one the educator's; the educator and the question drafted for
 * the coordinator are taken away after.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aWaitingSkill } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U32-MINE";
const OTHER = "U32-OTHER";
const ASK = "U32-FOR-THE-COORDINATOR";
const EDUCATOR = { email: "u32-educator@cornerstone.test", name: "U32 Educator", role: "educator", classes: [MINE] };
const PASSWORD = "u32-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let mine: Record<string, string>;
let other: Record<string, string>;
let draft: string;
let putBack: () => Promise<void>;
let sheet: string;

test.beforeAll(async () => {
  mine = await aClass(sql, MINE, "G2", ["Ira", "Jai"]);
  other = await aClass(sql, OTHER, "G2", ["Kavi", "Lata"]);
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
  // a question the engine drafted for the coordinator, not for an educator
  await sql`
    insert into ask (tenant_id, code, ord, for_role, question, drafted, source)
    select id, ${ASK}, 999, 'coordinator', 'Is this the coordinator''s to answer?', 'Yes.', 'u32' from tenant limit 1
    on conflict do nothing`;
  [{ code: draft }] = await sql<{ code: string }[]>`select code from skill_set order by code limit 1`;
  putBack = await aWaitingSkill(sql, draft);
  [{ code: sheet }] = await sql<{ code: string }[]>`
    select code from sheet_template
    where band = 'G2' and retired_at is null and code ~ '^[RMX][0-9]{1,2}-[EMHA][0-9]{2,3}$' order by code limit 1`;
});
test.afterAll(async () => {
  await putBack?.();
  await sql`delete from ask where code = ${ASK}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function signedIn(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

/** The count a menu tab carries, 0 when it carries none (as u15 reads it). */
async function badge(page: Page, tab: string): Promise<number> {
  const link = page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: new RegExp(`^${tab}\\b`) });
  const n = link.getByTestId("waiting");
  return (await n.count()) ? Number((await n.innerText()).replace(/\D/g, "")) : 0;
}

const waitingAsks = async (role: string | null) =>
  (await sql<{ n: number }[]>`select count(*)::int as n from ask where answer is null and (${role}::text is null or for_role = ${role})`)[0].n;
const waitingSkills = async () => (await sql<{ n: number }[]>`select count(*)::int as n from skill_set where status <> 'ratified'`)[0].n;

test("an educator's Today lists only what they may decide, and the menu counts the same", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    const main = page.getByRole("main");
    await expect(main).toContainText("Today");
    await expect(main, "approving a skill is the coordinator's").not.toContainText("Skills to approve");
    // Curriculum waits on the educator for their own questions only: none of the coordinator's, no skill to approve
    const theirs = await waitingAsks("educator");
    expect(await badge(page, "Curriculum"), "Curriculum's count is the educator's own questions").toBe(theirs);
    expect(await waitingAsks(null), "a question waits that is not theirs").toBeGreaterThan(theirs);
  } finally {
    await page.context().close();
  }
});

test("an educator is offered no approval of a skill", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    await page.goto(`/skill-sets/${draft}`);
    const main = page.getByRole("main");
    await expect(main).toContainText("Waiting for the coordinator’s approval");
    await expect(page.getByRole("button", { name: "Approve as written" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Change the words" }), "drafting stays the educator's").toBeVisible();

    await page.goto("/skill-sets/approve");
    await expect(page.getByRole("main")).toContainText("The coordinator approves the skills");
    await expect(page.getByRole("main").getByRole("button", { name: /approve/i })).toHaveCount(0);
  } finally {
    await page.context().close();
  }
});

test("a worksheet's print list names only the educator's own children, and no other name is read", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    const [{ t }] = await sql<{ t: Date }[]>`select now() as t`;
    await page.goto(`/worksheets/${sheet}`);
    const print = page.locator("section").filter({ has: page.getByRole("heading", { name: "Print for children" }) });
    await expect(print).toContainText("Ira");
    await expect(print).toContainText("Jai");
    await expect(print).not.toContainText("Kavi");
    await expect(print).not.toContainText("Lata");
    await expect(print.locator("legend"), "one class: theirs").toHaveText([MINE]);
    const read = await sql<{ child_id: string }[]>`
      select distinct child_id from access_log where actor = ${EDUCATOR.email} and occurred_at >= ${t}`;
    const ids = read.map((r) => r.child_id);
    expect(ids.filter((id) => Object.values(other).includes(id)), "no name of another class's child was read").toEqual([]);
    expect(ids.filter((id) => !Object.values(mine).includes(id)), "no child's name but their own class's").toEqual([]);
  } finally {
    await page.context().close();
  }
});

test("the coordinator is shown every decision and every class", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByRole("main")).toContainText("Skills to approve");
  expect(await badge(page, "Curriculum"), "every skill waiting and every question").toBe((await waitingSkills()) + (await waitingAsks(null)));

  await page.goto(`/skill-sets/${draft}`);
  await expect(page.getByRole("button", { name: "Approve as written" })).toBeVisible();

  await page.goto(`/worksheets/${sheet}`);
  const print = page.locator("section").filter({ has: page.getByRole("heading", { name: "Print for children" }) });
  for (const name of ["Ira", "Jai", "Kavi", "Lata"]) await expect(print).toContainText(name);
});
