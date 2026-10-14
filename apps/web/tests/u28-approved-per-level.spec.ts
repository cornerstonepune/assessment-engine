/**
 * U28 — questions approved level by level (goals/f1d-questions-approved-per-level.yaml, ADR 0073 D2). Nimish, 2026-10-14:
 * "If I just want to approve something for a grade level today, I'm not able to do that." The coordinator approves one
 * level of a skill on its page; that level says who approved it, the others still wait, and the skill waits until every
 * level is approved. An educator reads who a level waits for, and has no button to press.
 */
import { scryptSync } from "node:crypto";
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const EDUCATOR = { email: "u28-educator@cornerstone.test", name: "U28 Educator", role: "educator", classes: [] };
const PASSWORD = "u28-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let code: string;

test.beforeAll(async () => {
  [{ code }] = await sql<{ code: string }[]>`
    select code from skill_set where status = 'draft' and (select count(*) from jsonb_object_keys(difficulty)) >= 2
    order by code limit 1`;
  await sql`update skill_set set level_approved = '{}' where code = ${code}`;
});
test.afterAll(async () => {
  await sql`update skill_set set level_approved = '{}' where code = ${code}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

test("the coordinator approves one level and the others still wait", async ({ page }) => {
  await page.goto(`/skill-sets/${code}`);
  const easy = page.getByRole("region", { name: "Easy", exact: true });
  await easy.getByRole("button", { name: "Approve Easy" }).click();
  await expect(page).toHaveURL(/level_approved=Easy/);
  await expect(page.getByRole("region", { name: "Easy", exact: true })).toContainText("Approved · End-to-end test");
  const [s] = await sql<{ status: string; level_approved: Record<string, unknown> }[]>`
    select status, level_approved from skill_set where code = ${code}`;
  expect(Object.keys(s.level_approved)).toEqual(["Easy"]);
  expect(s.status, "the skill waits until every level is approved").toBe("draft");
  await expect(page.getByRole("region", { name: "Medium", exact: true }).getByRole("button", { name: "Approve Medium" })).toBeVisible();
});

test("an educator reads who a level waits for, and has no button", async ({ browser }) => {
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await page.goto("/login");
    await page.getByLabel("School email").fill(EDUCATOR.email);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/today$/);
    await page.goto(`/skill-sets/${code}`);
    const medium = page.getByRole("region", { name: "Medium", exact: true });
    await expect(medium).toContainText("Waiting for the coordinator");
    await expect(medium.getByRole("button")).toHaveCount(0);
  } finally {
    await context.close();
  }
});
