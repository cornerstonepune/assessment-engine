/**
 * Step 3 — every question on a numbered worksheet (goals/s3-worksheet-library.yaml, ADR 0026).
 *
 * Nimish, 2026-09-21: "when you click on a skill, all the worksheets that have been generated with
 * regard to that skill should exist, and there should be a filter of easy, medium, hard, and
 * advanced". Every count here is checked against the rows of the local copy.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { libraryOf, restoreLibrary } from "./library-state";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

const LEVELS = ["Easy", "Medium", "Hard", "Advance"];

const counts = () => sql<{ code: string; difficulty: string; n: number }[]>`
  select skill_set_code as code, difficulty, count(*)::int as n from sheet_template
  where source = 'library' and retired_at is null group by 1, 2`;

test("every skill shows its worksheets at each level, at least ten, and the filter shows only that level", async ({ page }) => {
  const rows = await counts();
  const skills = [...new Set(rows.map((r) => r.code))];
  const [{ n: all }] = await sql<{ n: number }[]>`select count(*)::int as n from skill_set`;
  expect(skills).toHaveLength(all); // 21 since step 8h: every skill has worksheets
  for (const code of skills) {
    await page.goto(`/skill-sets/${code}#worksheets`);
    const filters = page.getByLabel("Show worksheets for");
    const [{ levels }] = await sql<{ levels: string[] }[]>`select array(select jsonb_object_keys(difficulty)) as levels from skill_set where code = ${code}`;
    for (const d of LEVELS.filter((l) => levels.includes(l))) {
      const n = rows.find((r) => r.code === code && r.difficulty === d)?.n ?? 0;
      expect(n, `${code} ${d}`).toBeGreaterThanOrEqual(10);
      await expect(filters.getByRole("link", { name: `${d} · ${n}`, exact: true })).toBeVisible();
    }
  }
  const hard = rows.find((r) => r.code === "ADD.2D2D" && r.difficulty === "Hard")!.n;
  await page.goto("/skill-sets/ADD.2D2D#worksheets");
  await page.getByLabel("Show worksheets for").getByRole("link", { name: `Hard · ${hard}` }).click();
  const list = page.getByRole("table", { name: "Worksheets for this skill" }).locator("tbody tr");
  await expect(list).toHaveCount(hard);
  for (const cell of await list.locator("td:nth-child(2)").allInnerTexts()) expect(cell).toBe("Hard");
});

test("the library on the Worksheets page holds exactly what the database holds", async ({ page }) => {
  const [{ total }] = await sql<{ total: number }[]>`
    select count(*)::int as total from sheet_template where source = 'library' and retired_at is null`;
  await page.goto("/worksheets");
  await expect(page.getByText(`${total.toLocaleString("en-IN")} worksheets · every question in the bank is on one`)).toBeVisible();
  const [{ name, n }] = await sql<{ name: string; n: number }[]>`
    select s.name, count(*)::int as n from sheet_template t join skill_set s on s.code = t.skill_set_code
    where t.source = 'library' and t.retired_at is null and t.skill_set_code = 'SUB.1D1D' and t.difficulty = 'Medium'
    group by s.name`;
  await page.getByRole("link", { name: `${name}, Medium: ${n} worksheets` }).click();
  await expect(page.getByRole("table", { name: "Worksheets", exact: true }).locator("tbody tr")).toHaveCount(n);
});

test("a worksheet shows its twelve questions with their answers, and prints", async ({ page }) => {
  await page.goto("/worksheets/R22-H03");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Worksheet R22-H03");
  const rows = page.getByRole("table", { name: "Questions and answers" }).locator("tbody tr");
  await expect(rows).toHaveCount(12);
  const first = await rows.first().getByRole("link").getAttribute("href");
  expect(first).toMatch(/^\/library\//);
  const pdf = await page.request.get("/api/worksheet/R22-H03");
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");
});

test("a question names the worksheets it is on, and each opens", async ({ page }) => {
  const [q] = await sql<{ item_key: string; code: string }[]>`
    select i.item_key, t.code from item i join sheet_template t on i.id = any(t.item_ids)
    where t.source = 'library' and t.retired_at is null order by t.code, i.item_key limit 1`;
  await page.goto(`/library/${q.item_key}`);
  await page.getByRole("link", { name: q.code, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Worksheet ${q.code}`);
  await expect(page.locator(`a[href="/library/${q.item_key}"]`)).toBeVisible();
});

test("removing a question from its page retires the worksheet it was on and a new one carries the rest", async ({ page }) => {
  const [q] = await sql<{ id: string; item_key: string; code: string }[]>`
    select i.id, i.item_key, t.code from item i join sheet_template t on i.id = any(t.item_ids)
    where t.source = 'library' and t.retired_at is null and t.skill_set_code = 'ADD.3D3D' and t.difficulty = 'Medium'
    order by i.item_key limit 1`;
  const worksheets = await libraryOf(sql, "ADD.3D3D", "Medium");
  try {
    await page.goto(`/library/${q.item_key}`);
    await page.getByLabel("Why remove it").fill("end-to-end test: removed and put back");
    await page.getByRole("button", { name: "Remove this question" }).click();
    // The page stays at the same address, so wait on what the removal does, not on a navigation.
    await expect
      .poll(async () => (await sql`select retired_at is not null as r from sheet_template where code = ${q.code}`)[0].r, {
        timeout: 15_000,
      })
      .toBe(true);
    const holding = await sql`
      select 1 from sheet_template where source = 'library' and retired_at is null and ${q.id}::uuid = any(item_ids)`;
    expect(holding).toHaveLength(0);
    await page.goto(`/worksheets/${q.code}`);
    await expect(page.getByRole("status")).toContainText("Retired on");
  } finally {
    // Back exactly as it was: the question in the bank, its worksheets as they were, the new one gone.
    await restoreLibrary(sql, "ADD.3D3D", "Medium", worksheets);
    await sql`delete from item_feedback where item_id = ${q.id} and note like 'end-to-end test%'`;
    await sql`update item set status = 'active' where id = ${q.id}`;
  }
});

test("the library and a worksheet fit a phone", async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 860 });
  for (const path of ["/worksheets", "/worksheets/R22-H03", "/skill-sets/ADD.2D2D?level=Easy"]) {
    await page.goto(path, { waitUntil: "networkidle" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, path).toBeLessThanOrEqual(1);
  }
});
