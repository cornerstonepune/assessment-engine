/**
 * U21 — Children by topic, a class and the list (goals/ui4b2-class-by-topic.yaml). Nimish, 2026-10-11: "in the
 * Children tab, I think we need to now expand our thought process as more and more topics start coming in and need
 * help. It should be by topic or something." A class opens on its children against its topics, each topic opening the
 * class against its skills alone, in their place. (The Children list's own topic chips went with goals/ux10-declutter.yaml.)
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
  (await sql<{ name: string }[]>`select name from skill where rung_code = ${rung} and status is distinct from 'retired' limit 1`)[0].name;

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

// a child's "Needs help on" on the Children list, their class opened (goals/ux3-children-grouped.yaml); a table holds
// only the columns that have something in them (goals/ux10-declutter.yaml), so the cell is found under its heading
const standing = async (page: Page, who: string) => {
  const table = page.getByRole("table", { name: `${SECTION}: its children` });
  const row = table.locator(`tr[data-child="${kids[who]}"]`);
  await expect(row).toBeVisible();
  const heads = (await table.locator("thead th").allTextContents()).map((t) => t.trim().replace(/ ▾$/, ""));
  const help = (await row.locator("td").nth(heads.indexOf("Needs help on")).innerText()).trim();
  return [help];
};

// goals/ux10-declutter.yaml, Nimish 2026-10-22: the topic chips on Children are dropped. What the page said by topic it
// now says across every topic switched on, and a class's own page still reads topic by topic (the next test).
test("the Children list has no topic chips: it reads every topic switched on, whatever the address says", async ({ page }) => {
  for (const at of [`/growth?class=${SECTION}`, `/growth?class=${SECTION}&topic=DATA`]) {
    await page.goto(at);
    await expect(page.getByRole("navigation", { name: "Topic" }), at).toHaveCount(0);
    // Asha needs help on addition and subtraction: it shows, though the address asked for Data handling alone
    expect(await standing(page, "Asha"), at).toEqual([await nameOf("R24")]);
  }
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
  // and one click, from the topics above it, shows every topic again, in the skills' place (goals/ux4-class-and-child.yaml)
  await page.getByRole("navigation", { name: "Topic" }).getByRole("link", { name: "All topics" }).click();
  await expect(page).not.toHaveURL(/topic=/);
  await expect(byTopic).toBeVisible();
  await expect(steps).toHaveCount(0);
});
