/**
 * U27 — who decides what (goals/f1c-who-decides-what.yaml, ADR 0073 decision 3). Every decision is checked on the server
 * before it writes: the signer's role must be one `people.decides` names for it, and what it touches must be in one of
 * their classes. Educators draft skills and the coordinator approves them. A refused decision changes nothing and lands
 * on a page that says whose it is. The form is changed by hand here as anyone could: hiding a button is not the check.
 *
 * The classes are the test's own (tests/rows.ts), made once and kept; the educator is taken off the list after.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

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
  [{ code: draft }] = await sql<{ code: string }[]>`select code from skill_set where status = 'draft' order by code limit 1`;
});
test.afterAll(async () => {
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

test("an educator's approval of a skill is refused and changes nothing", async ({ browser, page: coordinator }) => {
  // an educator is offered no approval of a skill (goals/ux1-who-sees-what.yaml); the form the coordinator is offered,
  // sent by hand from the educator's own page, is what is refused
  await coordinator.goto(`/skill-sets/${draft}`);
  const approve = coordinator.getByRole("button", { name: "Approve as written" });
  const form = await coordinator.locator("form").filter({ has: approve }).evaluate((f) => f.outerHTML);
  const page = await signedIn(browser);
  try {
    await page.goto(`/skill-sets/${draft}`);
    await expect(page.getByRole("button", { name: "Approve as written" }), "not offered").toHaveCount(0);
    await page.evaluate((html) => {
      document.body.insertAdjacentHTML("beforeend", html);
      (document.body.lastElementChild as HTMLFormElement).submit();
    }, form);
    await expect(page).toHaveURL(/\/refused/);
    await expect(page.getByRole("main")).toContainText("Approving a skill");
    await expect(page.getByRole("main")).toContainText("a coordinator");
    const [now] = await sql<{ status: string }[]>`select status from skill_set where code = ${draft}`;
    expect(now.status, "the skill still waits for the coordinator").toBe("draft");
  } finally {
    await page.context().close();
    await sql`update skill_set set status = 'draft', ratified_by = null where code = ${draft}`;
  }
});

test("an educator cannot approve another class's pack by changing the form", async ({ browser }) => {
  const page = await signedIn(browser);
  try {
    await page.goto(`/papers/approve?section=${MINE}&week=${WEEK}&kind=practice`);
    const approve = page.getByRole("button", { name: /^Approve \d+ papers?\b/ });
    await expect(approve).toBeEnabled();
    // the class in the form, changed by hand to a class that is not theirs
    const form = page.locator("form").filter({ has: approve });
    await form.locator('input[name="section"]').evaluate((el, s) => ((el as HTMLInputElement).value = s), OTHER);
    await approve.click();
    await expect(page).toHaveURL(/\/refused/);
    await expect(page.getByRole("main")).toContainText("not one of your classes");
    const printed = await sql`
      select 1 from sheet_instance where child_id = any(${Object.values(other)}::uuid[]) and approved_by is not null`;
    expect(printed, "nothing of the other class was approved").toHaveLength(0);
  } finally {
    await page.context().close();
  }
});

test("the coordinator takes any decision", async ({ page }) => {
  try {
    await page.goto(`/skill-sets/${draft}`);
    await page.getByRole("button", { name: "Approve as written" }).click();
    await expect(page).toHaveURL(/approved=1/);
    const [now] = await sql<{ status: string }[]>`select status from skill_set where code = ${draft}`;
    expect(now.status).toBe("ratified");
  } finally {
    await sql`update skill_set set status = 'draft', ratified_by = null where code = ${draft}`;
  }
});
