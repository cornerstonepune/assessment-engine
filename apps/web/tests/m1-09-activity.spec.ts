/**
 * M1-09a — an activity's page in the educator's screens (goals/m1-09a-activity-page.yaml, D-076), on M1-12b's page
 * routes, each part drawn by the shared page-part component (#422). The school's own words are the real Insects sheet (ACT-K2-0348), copied to a code of the test's own; the parts
 * the sheet leaves empty carry drafts that are test placeholders, marked as a draft waiting for a person. No child.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { loadFortnight10, shoot, tapsAreBig, timetableSwitch } from "./educator-screens";
import { SECTION, k2Class } from "./k2-rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CODE = "ACT-K2-T09A";
const STEPS = ["Placeholder step: show the picture cards.", "Placeholder step: children sort them."];
const THINKING = { idea: "Placeholder idea: an insect has six legs.", slips: [{ keyword: "spider", spot: "Placeholder: a spider is counted as an insect." }] };
// as the engine's k2_format.render writes the text beside a list; the page trusts a list only while the two agree
const text = { steps: STEPS.map((s) => `• ${s}`).join("\n"), thinking: [THINKING.idea, ...THINKING.slips.map((s) => `• ${s.keyword}: ${s.spot}`)].join("\n") };

test.beforeAll(async () => {
  await k2Class(sql);
  loadFortnight10(SECTION);
});

test.beforeEach(async () => {
  await sql`delete from activity where code = ${CODE}`;
  await sql`
    insert into activity (tenant_id, code, band, strand, name, sheet_no, objective, steps, thinking, level_0, level_1, level_2, level_3, materials, steps_list, thinking_doc)
    select tenant_id, ${CODE}, band, strand, name, sheet_no, objective, ${text.steps}, ${text.thinking}, level_0, level_1, level_2, level_3, materials,
           ${sql.json(STEPS)}, ${sql.json(THINKING)}
    from activity where code = 'ACT-K2-0348'`;
  await sql`
    insert into activity_part_source (tenant_id, activity_code, part, source, check_me)
    select tenant_id, ${CODE}, p, 'drafted', true from activity, unnest(array['steps', 'thinking']) p where code = ${CODE}`;
});
test.afterAll(async () => {
  await sql`delete from activity where code = ${CODE}`;
  await timetableSwitch(sql, false);
  await sql.end();
});

test("while the timetable is switched off an activity's page is not found", async ({ page }) => {
  await timetableSwitch(sql, false);
  await page.goto(`/educator/activity/${CODE}`);
  await expect(page.getByText("This page could not be found.")).toBeVisible();
});

test("the page shows the school's words, drafted steps as bullets and how to think as an idea with slips, each draft marked check me", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator/activity/${CODE}`);
  await expect(page.getByRole("heading", { level: 1, name: "Insects" })).toBeVisible();
  const objective = page.locator('[data-part="objective"]');
  await expect(objective.locator(".pp-origin")).toHaveText("The school's words");
  await expect(objective.getByRole("button")).toHaveCount(0); // the school's words are never answered
  const steps = page.locator('[data-part="steps"]');
  await expect(steps.locator(".pp-origin")).toHaveText("Drafted, check me");
  await expect(steps.locator(".pp-steps li")).toHaveText(STEPS);
  const thinking = page.locator('[data-part="thinking"]');
  await expect(thinking).toContainText(THINKING.idea);
  await expect(thinking.locator("mark")).toHaveText("spider");
  for (const n of [0, 1, 2, 3]) await expect(page.getByRole("heading", { name: `Level ${n}` })).toBeVisible();
  await expect(page.locator("[data-summary]")).toContainText("2 parts to check");
  // no person is ever named on the page: not the member of staff who kept a part, not a child
  const [{ names }] = await sql<{ names: string[] }[]>`select coalesce(array_agg(name), '{}') as names from pii.staff`;
  const body = await page.locator("main").innerText();
  for (const n of names) expect(body, "a staff name on the page").not.toContain(n);
  await tapsAreBig(page);
  await shoot(page, "4-activity");
});

test("Keep makes a draft a person's, Edit puts her words in its place, and Send back empties it", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto(`/educator/activity/${CODE}`);
  const steps = page.locator('[data-part="steps"]');
  await steps.getByRole("button", { name: "Keep" }).click();
  await expect(steps.locator(".pp-origin")).toHaveText("Kept by a person");
  await expect(steps.getByRole("button", { name: "Keep" })).toHaveCount(0);

  const thinking = page.locator('[data-part="thinking"]');
  await thinking.getByText("Edit").click();
  await thinking.locator('input[name="idea"]').fill("Placeholder idea, in her words.");
  await thinking.getByRole("button", { name: "Save" }).click();
  await expect(thinking).toContainText("Placeholder idea, in her words.");
  await expect(thinking.locator(".pp-origin")).toHaveText("Kept by a person");

  await sql`update activity_part_source set source = 'drafted', check_me = true where activity_code = ${CODE} and part = 'steps'`;
  await page.reload();
  await steps.getByRole("button", { name: "Send back" }).click();
  await expect(steps).toContainText("Nothing written yet.");
  await expect(steps.locator(".pp-origin")).toHaveCount(0);
});

test("a period whose line names an activity opens its page, and back returns to the day", async ({ page }) => {
  await timetableSwitch(sql, true);
  const [p] = await sql<{ klass: string; day: string; period: string }[]>`
    select s.school_class_id::text as klass, d.on_date::text as day, s.period_id::text as period from session s
    join school_day d on d.id = s.school_day_id join plan_entry pe on pe.id = s.plan_entry_id
    join activity a on a.id = pe.activity_id where a.code = 'ACT-K2-0348' order by d.on_date limit 1`;
  expect(p, "Fortnight 10 names Insects on a period").toBeTruthy();
  await page.goto(`/educator/period/${p.period}?class=${p.klass}&day=${p.day}`);
  await page.locator("[data-open-activity]").click();
  await expect(page.getByRole("heading", { level: 1, name: "Insects" })).toBeVisible();
  await expect(page).toHaveURL(/\/educator\/activity\/ACT-K2-0348/);
  await page.locator('[data-ux="next"]').click();
  await expect(page).toHaveURL(new RegExp(`/educator\\?class=${p.klass}&day=${p.day}`));
});
