/**
 * The Assessments page by topic, and the names and stages of its rows (goals/asm2_by_topic_and_checking.yaml), at 1440 px.
 * Nimish, 26 Oct 2026: "There must be some view where I'll be able to just see the assessments by topic also. Let's say if
 * someone wants to go and see addition, they can see all the assessments under addition."
 *
 * A class of the test's own with twelve class assessments on one Addition & subtraction skill (a different week each) and two
 * on Multiplication, so a topic has more than a page of rows and another topic's rows can be told apart.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "ASM2-TOP";
const WEEKS = Array.from({ length: 12 }, (_, i) => `2025-W${String(10 + i).padStart(2, "0")}`);
const MUL_WEEKS = ["2025-W30", "2025-W31"];
let addSkill = "";
let addName = "";

test.beforeAll(async () => {
  const kids = await aClass(sql, SECTION, "G2", ["Asha"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const sheet = async (topic: string) => {
    const [w] = await sql<{ id: string; skill: string }[]>`
      select t.id, t.skill_set_code as skill from sheet_template t join skill s on s.tenant_id = t.tenant_id and s.code = t.skill_set_code
      where t.source = 'library' and t.retired_at is null and s.topic_code = ${topic} and t.band = 'G2'
      order by t.skill_set_code, t.difficulty, t.code limit 1`;
    return w;
  };
  const add = await sheet("ADDSUB");
  const mul = await sheet("MUL");
  if (!add || !mul) throw new Error("needs a Grade 2 library worksheet on Addition & subtraction and one on Multiplication");
  addSkill = add.skill;
  [{ name: addName }] = await sql<{ name: string }[]>`select name from skill where code = ${addSkill}`;
  const paper = (qr: string, template: string, week: string) => sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${tenant}, ${qr}, ${template}, ${kids.Asha}, ${week}, ${SECTION}, 'assessment', 'printed', 'asm2', now()
    where not exists (select 1 from sheet_instance where qr_code = ${qr})`;
  for (const [i, w] of WEEKS.entries()) await paper(`CSB2A${String(i).padStart(3, "0")}`, add.id, w);
  for (const [i, w] of MUL_WEEKS.entries()) await paper(`CSB2B${String(i).padStart(3, "0")}`, mul.id, w);
});
test.afterAll(async () => sql.end());

const topicRow = (page: import("@playwright/test").Page, code: string) => page.locator(`tr[data-topic='${code}']`);

test("a By topic view lists the topics collapsed, each with its count, next to the list", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}`);
  const views = page.locator("[data-views]");
  await expect(views.getByRole("link")).toHaveText(["All assessments", "By topic"]);
  await views.getByRole("link", { name: "By topic" }).click();
  await expect(page).toHaveURL(/view=topic/);
  await expect(views.getByRole("link", { name: "By topic" })).toHaveAttribute("aria-current", "page");
  const table = page.getByRole("table", { name: "Assessments by topic" });
  await expect(table.locator("thead th")).toContainText(["Topic", "Subject", "Assessments"]);
  const add = topicRow(page, "ADDSUB");
  await expect(add).toContainText("Addition & subtraction");
  await expect(add.locator("td[data-label='Assessments']")).toHaveText("12");
  await expect(topicRow(page, "MUL").locator("td[data-label='Assessments']")).toHaveText("2");
  // collapsed: no topic's assessments are drawn, and each topic says it is closed
  await expect(page.locator("tr[data-assessment]")).toHaveCount(0);
  await expect(add.locator("a[aria-expanded]")).toHaveAttribute("aria-expanded", "false");
  // the view is a place of its own, with the filters inside the page
  await expect(page.locator("[data-filterbar]")).toContainText("Class");
});

test("opening a topic shows only its assessments, ten to a page, and no other topic's rows are read", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}&view=topic`);
  await topicRow(page, "ADDSUB").locator("a[aria-expanded]").click();
  await expect(page).toHaveURL(/t=ADDSUB/);
  const rows = page.locator("[data-topic-rows='ADDSUB'] tr[data-assessment]");
  await expect(rows).toHaveCount(10);
  // all of them Addition & subtraction; none of Multiplication's two is read or drawn
  await expect(page.locator("tr[data-assessment]")).toHaveCount(10);
  for (const name of await rows.locator("a[aria-expanded]").allInnerTexts()) expect(name).toContain(addName);
  await expect(page.locator("[data-topic-rows='MUL']")).toHaveCount(0);
  await expect(page.getByText("Page 1 of 2")).toBeVisible();
  // the newest week first
  const first = await rows.first().getAttribute("data-assessment");
  expect(first).toContain(`~${WEEKS[11]}~`);
  await page.getByRole("link", { name: "Later →" }).click();
  await expect(page.locator("tr[data-assessment]")).toHaveCount(2);
  await expect(page.getByText("Page 2 of 2")).toBeVisible();
  // closing it again leaves every topic collapsed
  await topicRow(page, "ADDSUB").locator("a[aria-expanded]").click();
  await expect(page.locator("tr[data-assessment]")).toHaveCount(0);
});

test("the name an educator gave wins, and the composition (every skill and level) is in the detail view, not the title", async ({ page }) => {
  // built: the topic, the skill, the kind and the class, never a list of digit sizes (a week no test renames)
  await page.goto(`/papers?class=${SECTION}&week=${WEEKS[1]}`);
  const built = page.locator(`tr[data-assessment^='assessment~${SECTION}~${WEEKS[1]}~']`).locator("a[aria-expanded]");
  await expect(built).toContainText("Addition & subtraction");
  await expect(built).toContainText(addName);
  await expect(built).toContainText("Class assessment");
  await expect(built).toContainText(SECTION);
  await built.click();
  await expect(page.locator("[data-copies] [data-composition]")).toContainText(addName);
  // the educator's own name wins
  const week = WEEKS[0];
  await page.goto(`/papers?class=${SECTION}&week=${week}`);
  const row = page.locator(`tr[data-assessment^='assessment~${SECTION}~${week}~']`);
  await row.getByText("Rename").click();
  await row.getByLabel("Name this assessment").fill("Week 10 addition check");
  await row.getByRole("button", { name: "Save" }).click();
  await expect(page.locator(`tr[data-assessment^='assessment~${SECTION}~${week}~'] a[aria-expanded]`)).toHaveText("Week 10 addition check");
});

test("each assessment shows the seven steps in order, each a chip; the stage and the class filter live inside the page", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}&view=topic&t=MUL`);
  const heads = (await page.locator("[data-topic-rows] thead th").allInnerTexts()).map((h) => h.trim());
  const steps = ["Created", "Printed", "Uploaded", "Read", "Checked", "Results in"];
  const at = steps.map((s) => heads.indexOf(s));
  expect(
    at.every((i) => i >= 0),
    `steps in ${heads}`,
  ).toBe(true);
  expect(
    [...at].sort((a, b) => a - b),
    "in order",
  ).toEqual(at);
  const chips = page.locator("[data-topic-rows='MUL'] tr[data-assessment]").first().locator("[data-status]");
  expect(await chips.count()).toBeGreaterThanOrEqual(5);
  for (let i = 0; i < (await chips.count()); i++) await expect(chips.nth(i).locator("svg[data-icon]")).toHaveCount(1);
  // the stage filter: the papers are printed and not yet in, so they are "Printed, to upload"
  const stage = page.locator("[data-filterbar] select[name=status]");
  await stage.selectOption("upload");
  await expect(page).toHaveURL(/status=upload/);
  await expect(page.locator("tr[data-assessment]")).toHaveCount(2);
  await stage.selectOption("check");
  await expect(page.locator("tr[data-assessment]")).toHaveCount(0);
  await expect(page.getByText(/Nothing in .* matches these filters/)).toBeVisible();
  // the class filter is in the same bar
  await expect(page.locator("[data-filterbar] select[name=class]")).toHaveValue(SECTION);
  await page.goto(`/papers?class=NO-SUCH-CLASS&view=topic`);
  await expect(page.locator("tr[data-topic]")).toHaveCount(0);
  await expect(page.getByText("Nothing matches these filters.")).toBeVisible();
});
