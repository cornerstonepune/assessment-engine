/**
 * U21 — Children by topic, a class and the list (goals/ui4b2-class-by-topic.yaml). Nimish, 2026-10-11: "in the
 * Children tab, I think we need to now expand our thought process as more and more topics start coming in and need
 * help. It should be by topic or something." The Children list reads one topic at a time, chosen at the top; a class
 * opens on its children against its topics, each topic opening the class against its skills alone.
 *
 * The class is the test's own (tests/rows.ts). Its children's skill states are set here directly — the graph's own
 * rules are proved by the engine's tests; this is how the pages lay them out — and taken away after.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U21-TEST";
let kids: Record<string, string> = {};
// child, rung, skill, state, answers, right: Asha needs help on and is secure in Addition & subtraction and secure in
// Data handling; Bina is practising in Addition & subtraction and has no answer in Data handling
const STATES: [string, string, string, string, number, number][] = [
  ["Asha", "R24", "NUM.OPS.02", "patterned_error", 6, 2],
  ["Asha", "R22", "NUM.OPS.01", "secure", 10, 10],
  ["Asha", "R34", "NUM.DATA.01", "secure", 8, 8],
  ["Bina", "R21", "NUM.OPS.01", "practising", 5, 3],
];
const nameOf = async (rung: string) =>
  (await sql<{ name: string }[]>`select name from skill_set where rung_code = ${rung} and status is distinct from 'retired' limit 1`)[0].name;

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select tenant_id from child where id = ${kids.Asha}`;
  await sql`delete from child_skill_state where child_id in (${kids.Asha}, ${kids.Bina})`;
  for (const [who, rung, skill, state, n, right] of STATES) {
    await sql`
      insert into child_skill_state (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, last_seen)
      values (${tenant_id}, ${kids[who]}, ${skill}, ${rung}, ${state}, ${n}, ${right}, now())`;
  }
});
test.afterAll(async () => {
  await sql`delete from child_skill_state where child_id in (${kids.Asha}, ${kids.Bina})`;
  await sql.end();
});

// a child's row on the Children list, their class opened (goals/ux3-children-grouped.yaml): needs help on, secure,
// practising
const standing = async (page: Page, who: string) => {
  const group = page.locator(`details[data-class="${SECTION}"]`);
  if ((await group.getAttribute("open")) === null) await group.locator("summary").click();
  const row = page.getByRole("table", { name: `${SECTION}: its children` }).locator(`tr[data-child="${kids[who]}"]`);
  await expect(row).toBeVisible();
  const cells = (await row.locator("td").allInnerTexts()).map((t) => t.trim());
  return [cells[2], cells[5], cells[4]];
};

test("the Children list reads one topic at a time", async ({ page }) => {
  await page.goto("/growth");
  const topics = page.getByRole("navigation", { name: "Topic" });
  await expect(topics.getByRole("link", { name: "All topics" })).toHaveAttribute("aria-current", "page");
  // every topic with a skill switched on, and none with none (taught skill by skill: goals/t1-topics-are-operations.yaml)
  const taught = (
    await sql<{ name: string }[]>`
      select distinct t.name from topic t join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
      where s.taught order by 1`
  ).map((t) => t.name);
  for (const t of taught) await expect(topics.getByRole("link", { name: t, exact: true })).toBeVisible();
  await expect(topics).not.toContainText("Multiples & factors");
  expect(await standing(page, "Asha")).toEqual([await nameOf("R24"), "2", "0"]);

  await topics.getByRole("link", { name: "Data handling", exact: true }).click();
  await expect(page).toHaveURL(/[?&]topic=DATA\b/);
  await expect(page.getByRole("navigation", { name: "Topic" }).getByRole("link", { name: "Data handling", exact: true })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(await standing(page, "Asha")).toEqual(["—", "1", "0"]);
  expect(await standing(page, "Bina")).toEqual(["—", "0", "0"]);

  await page.getByRole("navigation", { name: "Topic" }).getByRole("link", { name: "Addition & subtraction", exact: true }).click();
  await expect(page).toHaveURL(/[?&]topic=ADDSUB\b/);
  expect(await standing(page, "Asha")).toEqual([await nameOf("R24"), "1", "0"]);
  expect(await standing(page, "Bina")).toEqual([await nameOf("R21"), "0", "1"]);
  // a sort keeps the topic
  await expect(page.getByRole("table", { name: `${SECTION}: its children` }).getByRole("link", { name: "Secure" })).toHaveAttribute(
    "href",
    /topic=ADDSUB/,
  );
});

test("a class opens on its children against its topics, and a topic opens its skills alone", async ({ page }) => {
  await page.goto(`/growth/class/${SECTION}`);
  const byTopic = page.getByRole("table", { name: `${SECTION}: each child on each topic` });
  await expect(byTopic.locator("thead th")).toHaveText(["Child", "Addition & subtraction", "Data handling"]);
  const cell = (who: string, topic: string) => byTopic.locator(`tr[data-child="${kids[who]}"] td[data-topic="${topic}"]`);
  await expect(cell("Asha", "ADDSUB")).toHaveText(/1 needs help[^]*1 secure/);
  await expect(cell("Asha", "ADDSUB")).toHaveAttribute("data-rag", "red");
  await expect(cell("Asha", "DATA")).toHaveText(/1 secure/);
  await expect(cell("Bina", "ADDSUB")).toHaveText(/1 practising/);
  await expect(cell("Bina", "ADDSUB")).toHaveAttribute("data-rag", "amber");
  await expect(cell("Bina", "DATA")).toHaveText("—");
  // no count is a colour alone: each has its mark, said in words
  await expect(cell("Asha", "ADDSUB").getByRole("img")).toHaveCount(2);

  // a topic opens the class against its skills alone
  await byTopic.getByRole("link", { name: "Data handling", exact: true }).click();
  await expect(page).toHaveURL(/[?&]topic=DATA\b/);
  const steps = page.getByRole("table", { name: `${SECTION}: each child on each step` });
  await expect(steps.locator("thead th[data-col]")).toHaveCount(1);
  expect(await steps.locator("thead th[data-col]").getAttribute("data-col")).toBe("NUM.DATA.01|R34");
  // and one click shows every topic's skills again
  await page.getByRole("link", { name: "Every topic’s skills" }).click();
  await expect(page).not.toHaveURL(/topic=/);
  await expect(steps.locator("thead th[data-col]")).toHaveCount(4); // R21, R22, R24 and R34
});
