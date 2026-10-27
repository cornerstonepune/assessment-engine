/**
 * U27 — who decides what (goals/f1c-who-decides-what.yaml, ADR 0073 decision 3), for now one role
 * (goals/ux9c-one-role.yaml). Nimish, 2026-10-22: "Just keep all the features available for both educators and
 * coordinators for now." Every decision is still checked on the server before it writes, through the one place that
 * says who may (`lib/access.ts`); today it says every member of staff may take every decision, on every class, and the
 * decision is in their own name.
 *
 * The classes are the test's own (tests/rows.ts), made once and kept; the educator is taken off the list after.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aWaitingSkill } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U27-MINE";
const OTHER = "U27-OTHER";
const WEEK = "2026-W42";
const EDUCATOR = { email: "u27-educator@cornerstone.test", name: "U27 Educator", role: "educator", classes: [MINE] };
const PASSWORD = "u27-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let mine: Record<string, string>;
let other: Record<string, string>;
let draft: string;
let putBack: () => Promise<void>;

test.beforeAll(async () => {
  mine = await aClass(sql, MINE, "G2", ["Esha", "Farhan"]);
  other = await aClass(sql, OTHER, "G3", ["Gauri", "Harsh"]);
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
  // a week of class practice planned for each class, as `engine week prescribe` plans one, and assembled: each child's
  // paper made and waiting to be approved, so the pack's button has papers to approve
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  const [w] = await sql<{ id: string }[]>`
    select id from sheet_template where source = 'library' and retired_at is null order by code limit 1`;
  for (const [section, kids] of [[MINE, mine], [OTHER, other]] as const) {
    for (const id of Object.values(kids)) {
      const [had] = await sql`select 1 from prescription where child_id = ${id} and week = ${WEEK}`;
      if (had) continue;
      const [{ id: paper }] = await sql<{ id: string }[]>`
        insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status)
        values (${tenant}, ${`U27-${id.slice(0, 8)}`}, ${w.id}, ${id}, ${WEEK}, ${section}, 'practice', 'new')
        returning id`;
      await sql`
        insert into prescription (tenant_id, child_id, week, rule_fired, skill_set_code, difficulty, kind, sheet_instance_id)
        values (${tenant}, ${id}, ${WEEK}, 'band_default', 'ADD.2D1D', 'Easy', 'practice', ${paper})`;
    }
  }
  [{ code: draft }] = await sql<{ code: string }[]>`select code from skill order by code limit 1`;
  putBack = await aWaitingSkill(sql, draft);
});
test.afterAll(async () => {
  await putBack?.();
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

test("an educator approves a skill, in their own name", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    await page.goto(`/skill-sets/${draft}`);
    await page.getByRole("button", { name: /^Approve, as / }).click();
    await expect(page).toHaveURL(/approved=1/);
    const [now] = await sql<{ status: string; ratified_by: string }[]>`select status, ratified_by from skill where code = ${draft}`;
    expect(now).toEqual({ status: "ratified", ratified_by: EDUCATOR.name });
  } finally {
    await page.context().close();
    // waiting again for the coordinator's test after this one, as `aWaitingSkill` left it
    await sql`update skill set status = 'draft', ratified_by = null, level_approved = '{}'::jsonb where code = ${draft}`;
  }
});

test("an educator's approval of another class's pack is refused in words, and nothing is approved", async ({ browser }) => {
  // since 27 Oct 2026 a class's papers are its own educators' and the coordinator's (goals/own_who_sees_answers.yaml)
  const page = await signedIn(browser);
  try {
    await page.goto(`/papers/approve?section=${OTHER}&week=${WEEK}&kind=practice`);
    await expect(page.getByRole("main")).toContainText("not one of your classes");
    // what the page shows instead is the educator's own class: nothing of the other class is offered
    await expect(page.locator(`form input[value="${OTHER}"]`)).toHaveCount(0);
    const [{ n }] = await sql<{ n: number }[]>`
      select count(*)::int as n from sheet_instance where child_id = any(${Object.values(other)}::uuid[]) and approved_by = ${EDUCATOR.email}`;
    expect(n).toBe(0);
  } finally {
    await page.context().close();
    await sql`update sheet_instance set print_status = 'new', printed_at = null, approved_by = null, approved_at = null
              where child_id = any(${Object.values(other)}::uuid[]) and week = ${WEEK}`;
  }
});

test("the coordinator takes any decision", async ({ page }) => {
  try {
    await page.goto(`/skill-sets/${draft}`);
    await page.getByRole("button", { name: /^Approve, as / }).click();
    await expect(page).toHaveURL(/approved=1/);
    const [now] = await sql<{ status: string }[]>`select status from skill where code = ${draft}`;
    expect(now.status).toBe("ratified");
  } finally {
    await sql`update skill set status = 'draft', ratified_by = null where code = ${draft}`;
  }
});
