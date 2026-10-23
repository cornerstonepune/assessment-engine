/**
 * U32 — who sees what (goals/ux1-who-sees-what.yaml), for now one role (goals/ux9c-one-role.yaml). Nimish, 2026-10-22:
 * "Achal sir is the educator coordinator right now. Just keep all the features available for both educators and
 * coordinators for now." An educator is shown what the coordinator is: every decision, every class, every question the
 * engine drafted, and Today and the menu count the same lines. Until 2026-10-22 this file held the reverse (UX1).
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
let draft: string;
let putBack: () => Promise<void>;
let sheet: string;

test.beforeAll(async () => {
  await aClass(sql, MINE, "G2", ["Ira", "Jai"]);
  await aClass(sql, OTHER, "G2", ["Kavi", "Lata"]);
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
  [{ code: draft }] = await sql<{ code: string }[]>`select code from skill order by code limit 1`;
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
const waitingSkills = async () => (await sql<{ n: number }[]>`select count(*)::int as n from skill where status <> 'ratified'`)[0].n;

test("an educator's Today lists every decision the coordinator's does, and the menu counts the same", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    const main = page.getByRole("main");
    await expect(main).toContainText("Skills to approve");
    // the menu carries a count on Today alone (goals/ux10-declutter.yaml): it holds every skill waiting and every question
  expect(await badge(page, "Today"), "every skill waiting and every question").toBeGreaterThanOrEqual((await waitingSkills()) + (await waitingAsks(null)));
  expect(await badge(page, "Curriculum"), "no count on Curriculum").toBe(0);
  } finally {
    await page.context().close();
  }
});

test("an educator is offered the approval of a skill", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    await page.goto(`/skill-sets/${draft}`);
    await expect(page.getByRole("button", { name: /^Approve, as / })).toBeVisible();
    await page.goto("/skill-sets/approve");
    await expect(page.getByRole("main")).not.toContainText("The coordinator approves the skills");
  } finally {
    await page.context().close();
  }
});

test("a worksheet's print list opens on the educator's own children, every class's one tap away", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    await page.goto(`/worksheets/${sheet}`);
    const print = page.locator("section").filter({ has: page.getByRole("heading", { name: "Print for children" }) });
    await expect(print).toContainText("Ira");
    await expect(print).not.toContainText("Kavi");
    await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST"),
      page.getByRole("search", { name: "Subject, class and search" }).getByLabel("Class").selectOption("every"),
    ]);
    await page.waitForLoadState("networkidle");
    for (const name of ["Ira", "Jai", "Kavi", "Lata"]) await expect(print).toContainText(name);
  } finally {
    await page.context().close();
  }
});

test("the coordinator is shown every decision and every class", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByRole("main")).toContainText("Skills to approve");
  // the menu carries a count on Today alone (goals/ux10-declutter.yaml): it holds every skill waiting and every question
  expect(await badge(page, "Today"), "every skill waiting and every question").toBeGreaterThanOrEqual((await waitingSkills()) + (await waitingAsks(null)));
  expect(await badge(page, "Curriculum"), "no count on Curriculum").toBe(0);

  await page.goto(`/skill-sets/${draft}`);
  await expect(page.getByRole("button", { name: /^Approve, as / })).toBeVisible();

  await page.goto(`/worksheets/${sheet}`);
  const print = page.locator("section").filter({ has: page.getByRole("heading", { name: "Print for children" }) });
  for (const name of ["Ira", "Jai", "Kavi", "Lata"]) await expect(print).toContainText(name);
});
