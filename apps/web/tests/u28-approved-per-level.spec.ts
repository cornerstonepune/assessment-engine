/**
 * U28 — questions approved level by level (goals/f1d-questions-approved-per-level.yaml, ADR 0073 D2). Nimish, 2026-10-14:
 * "If I just want to approve something for a grade level today, I'm not able to do that." The coordinator approves one
 * level of a skill on its page; that level says who approved it, the others still wait, and the skill waits until every
 * level is approved. An educator reads who a level waits for, and has no button to press.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aWaitingSkill } from "./rows";
import { signIn } from "./sign-in";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const EDUCATOR = { email: "u28-educator@cornerstone.test", name: "U28 Educator", role: "educator", classes: [] };
let code: string;
let putBack: () => Promise<void>;

test.beforeAll(async () => {
  [{ code }] = await sql<{ code: string }[]>`
    select code from skill_set where (select count(*) from jsonb_object_keys(difficulty)) >= 2 order by code limit 1`;
  putBack = await aWaitingSkill(sql, code);
});
test.afterAll(async () => {
  await putBack?.();
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

test("an educator is offered each level's approval, as the coordinator is (one role for now, goals/ux9c-one-role.yaml)", async ({ browser }) => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([EDUCATOR])}
    where key = 'app.staff'`;
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await signIn(page, EDUCATOR.email);
    await expect(page).toHaveURL(/\/today$/);
    await page.goto(`/skill-sets/${code}`);
    const medium = page.getByRole("region", { name: "Medium", exact: true });
    await expect(medium.getByRole("button", { name: "Approve Medium" })).toBeVisible();
  } finally {
    await context.close();
  }
});
