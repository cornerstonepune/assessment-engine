/**
 * M1-09m — the materials pages in the educator's screens (goals/m1-09m-materials.yaml, D-076): her class's list built
 * by M1-10's engine from Fortnight 10 as the school wrote it, the school's list for the month and the notes waiting
 * for a person (M1-16). Catalogue items are the tests' own, tied to the real activities. No child; no send screen.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { loadFortnight10, materialsFor, shoot, tapsAreBig, timetableSwitch } from "./educator-screens";
import { SECTION, k2Class } from "./k2-rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const TUESDAY = "2026-12-01"; // Fortnight 10, week B: tulips today, the dustbin tomorrow, beads on Thursday
let klass = "";
let staff = "";

test.beforeAll(async () => {
  ({ klass, staff } = await k2Class(sql));
  loadFortnight10(SECTION);
  await materialsFor(sql);
  // a grant is never deleted, only ended (the table refuses a delete): end any this test left open
  await sql`update staff_role_grant set valid_to = valid_from where staff_id = ${staff} and granted_by = 'm1-09m test' and valid_to is null`;
});
test.afterAll(async () => {
  await sql`update staff_role_grant set valid_to = valid_from where staff_id = ${staff} and granted_by = 'm1-09m test' and valid_to is null`;
  await timetableSwitch(sql, false);
  await sql.end();
});

const open = (page: Page, span = "fortnight") => page.goto(`/educator/materials?class=${klass}&day=${TUESDAY}&span=${span}`);
// Each test starts from the plan: a line is never deleted (its edits point at it), so the class's lines go back to the
// plan's quantities, the plan's lines back on the list and lines she added off it.
test.beforeEach(async () => {
  await sql`
    update materials_line l set
      removed_at = case when l.source = 'educator' then coalesce(l.removed_at, now()) else null end,
      quantity = case when l.source = 'school' then (select sum(s.quantity) from materials_line_source s where s.line_id = l.id) else l.quantity end
    where l.list_id in (select id from materials_list where school_class_id = ${klass})`;
});

const line = (page: Page, item: string) => page.locator("tr[data-line]").filter({ hasText: item });

test("while the timetable is switched off the class list is not found", async ({ page }) => {
  await timetableSwitch(sql, false);
  await open(page);
  await expect(page.getByText("This page could not be found.")).toBeVisible();
});

test("the class list is a table a day, each line tied to its activity, its quantity never guessed and where it is kept", async ({ page }) => {
  await timetableSwitch(sql, true);
  await open(page);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Materials");
  await expect(page.locator("#lines h3")).toHaveCount(3); // a table a day
  await expect(line(page, "Craft paper").locator('input[name="quantity"]')).toHaveValue("2");
  await expect(line(page, "Craft paper").locator("[data-home]")).toHaveAttribute("data-home", "school");
  await expect(line(page, "Dustbin").locator("[data-home]")).toHaveAttribute("data-home", "class");
  await expect(line(page, "Beads").locator('input[name="quantity"]')).toHaveValue(""); // the plan gives none
  await expect(line(page, "Beads").locator("[data-home]")).toHaveAttribute("data-home", "none");
  await expect(line(page, "Dustbin").getByRole("link", { name: "Proper Use Of Dustbin" })).toHaveAttribute("href", /\/educator\/activity\/ACT-K2-0287/);
  await expect(page.locator("[data-summary]")).toContainText("1 without a quantity");
  await expect(page.getByRole("button", { name: /WhatsApp|Send/ })).toHaveCount(0);
  await tapsAreBig(page);
  await shoot(page, "5-materials");
});

test("a quantity she sets is kept, a line removed is gone, an item added from the catalogue is on the list", async ({ page }) => {
  await timetableSwitch(sql, true);
  await open(page);
  await line(page, "Beads").locator('input[name="quantity"]').fill("3");
  await line(page, "Beads").getByRole("button", { name: "Save" }).click();
  await expect(line(page, "Beads").locator('input[name="quantity"]')).toHaveValue("3");
  await line(page, "Dustbin").getByRole("button", { name: /Remove/ }).click();
  await expect(line(page, "Dustbin")).toHaveCount(0);
  // an item of this run's own, so a line she added on an earlier run is never in the way
  const name = `Placeholder glue ${Date.now()}`;
  await sql`insert into material_item (tenant_id, code, name, unit) select tenant_id, ${`MAT-M109-G${Date.now()}`}, ${name}, 'piece' from school_class where id = ${klass}`;
  await page.reload();
  await page.locator('[data-add] select[name="code"]').selectOption({ label: name });
  await page.locator("[data-add]").getByRole("button", { name: "Add" }).click();
  await expect(line(page, name)).toHaveCount(1);
  await page.reload();
  await expect(line(page, "Beads").locator('input[name="quantity"]')).toHaveValue("3");
});

test("the school's list and the notes to read are the coordinator's: anyone else is told so, the coordinator sees them", async ({ page }) => {
  await timetableSwitch(sql, true);
  await page.goto("/educator/materials/school?month=2026-12");
  await expect(page.getByText("The school's list is the coordinator's.")).toBeVisible();
  await page.goto("/educator/materials/review");
  await expect(page.getByText("Notes are read by the coordinator.")).toBeVisible();
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from school_class where id = ${klass}`;
  await sql`insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by) values (${tenant}, ${staff}, 'coordinator', current_date - 1, 'm1-09m test')`;
  await open(page);
  const [{ id: list }] = await sql<{ id: string }[]>`select id from materials_list where school_class_id = ${klass} order by created_at desc limit 1`;
  await sql`insert into materials_note_review (tenant_id, list_id, text, reason, who) values (${tenant}, ${list}, 'Placeholder note: two dozen lolly sticks', 'Placeholder: lolly sticks are not in the catalogue', ${staff})`;
  await page.goto("/educator/materials/school?month=2026-12");
  await expect(page.locator("[data-school-list] tr[data-line]").first()).toBeVisible();
  await shoot(page, "6-school-list");
  await page.goto("/educator/materials/review");
  const note = page.locator("tr[data-note]").filter({ hasText: "lolly sticks" });
  await expect(note).toBeVisible();
  await shoot(page, "7-notes-to-read");
  await note.locator('input[name="why"]').fill("Placeholder: asked again in class");
  await note.getByRole("button", { name: "Set aside" }).click();
  await expect(page.locator("tr[data-note]").filter({ hasText: "lolly sticks" })).toHaveCount(0);
});

test("while switched off a previewer sees her class's real list and the school's, to look at only, and nothing is kept", async ({ page }) => {
  await timetableSwitch(sql, false);
  // her own role made a previewing one, and one the school's list is for (both config rows, put back after): a grant
  // is never deleted, so the test changes the rows, not her grants
  const rows = await sql<{ key: string; value: unknown }[]>`select key, value from config where key in ('educator.preview_roles', 'materials.consolidate_roles')`;
  await sql`update config set value = value || '["class_teacher"]'::jsonb where key in ('educator.preview_roles', 'materials.consolidate_roles')`;
  try {
    const kept = async () => (await sql<{ n: number }[]>`select (select count(*) from materials_list) + (select count(*) from materials_line) + (select count(*) from materials_consolidated) as n`)[0].n;
    const before = await kept();
    await open(page);
    await expect(line(page, "Craft paper")).toContainText("2 sheet");
    await expect(page.getByRole("button", { name: /Save|Remove|Add/ })).toHaveCount(0); // a preview changes nothing
    await page.goto("/educator/materials/school?month=2026-12");
    await expect(page.locator("[data-school-list] tr[data-line]").first()).toBeVisible();
    expect(await kept()).toBe(before);
  } finally {
    for (const r of rows) await sql`update config set value = ${sql.json(r.value as never)} where key = ${r.key}`;
  }
});
