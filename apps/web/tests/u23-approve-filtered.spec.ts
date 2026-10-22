/**
 * U23 — Approving the skills, as a table to work through (goals/ui6a-approve-filtered.yaml). Nimish, 2026-10-12, with a
 * screenshot of the page: "also ths page needs to have proper filters and all; no page should have such laundary lists
 * like stuff". Each waiting skill one row, its levels folded until opened; grade, topic and taught narrow the rows;
 * "Approve these" approves the rows shown and nothing else. Every change is put back after.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const DRAFTS = ["ADD.1D1D", "ADD.2D2D", "SUB.2D2D", "DIV.3D1D"];

test.afterAll(async () => {
  await sql.end();
});

// every skill approved but these, the mistake table as it was; put back after
async function onlyThese(run: () => Promise<void>) {
  const before = await sql<{ code: string; status: string; ratified_by: string | null }[]>`
    select code, status, ratified_by from skill order by code`;
  const [table] = await sql<{ value: unknown }[]>`select value from config where key = 'skills.charges_by_kind.approved'`;
  try {
    await sql`update skill set status = 'ratified', ratified_by = 'someone earlier'`;
    await sql`update skill set status = 'draft', ratified_by = null where code = any(${DRAFTS})`;
    await run();
  } finally {
    for (const b of before) {
      await sql`update skill set status = ${b.status}, ratified_by = ${b.ratified_by} where code = ${b.code}`;
    }
    await sql`update config set value = ${sql.json((table?.value ?? {}) as never)} where key = 'skills.charges_by_kind.approved'`;
  }
}

const rows = (page: Page) => page.getByRole("table", { name: "Skills waiting for approval" }).locator("tbody tr");
// the rows the page shows once it has loaded: the count is waited for, then each row's skill read
async function expectRows(page: Page, codes: string[]) {
  await expect(rows(page)).toHaveCount(codes.length);
  const shown = await rows(page).evaluateAll((trs) => trs.map((tr) => tr.getAttribute("data-row")));
  expect(shown.sort()).toEqual([...codes].sort());
}

test("each waiting skill is one row, its levels folded until opened", async ({ page }) => {
  await onlyThese(async () => {
    await page.goto("/skill-sets/approve");
    await expectRows(page, DRAFTS);
    // no skill is a card of its own any more
    const [{ name }] = await sql<{ name: string }[]>`select name from skill where code = 'ADD.2D2D'`;
    await expect(page.getByRole("region", { name, exact: true })).toHaveCount(0);
    const row = rows(page).and(page.locator('[data-row="ADD.2D2D"]'));
    await expect(row.getByRole("rowheader")).toHaveText(name);
    await expect(row).toContainText("Grade 2");
    const easy = row.getByText("Easy", { exact: true });
    await expect(easy).toBeHidden();
    await row.getByText("Read the levels").click();
    await expect(easy).toBeVisible();
    await expect(row.getByRole("button", { name: `Approve, as ${TEST_STAFF.name}` })).toBeVisible();
    await expect(row.getByRole("link", { name: "Change the words first" })).toHaveAttribute("href", "/skill-sets/ADD.2D2D/edit");
    // a skill whose topic is not taught yet says so on its row
    await expect(rows(page).and(page.locator('[data-row="DIV.3D1D"]'))).toContainText("Not taught yet");
  });
});

test("a grade and a topic narrow the rows, and approving these approves only the rows shown", async ({ page }) => {
  await onlyThese(async () => {
    const [{ value: tableBefore }] = await sql<{ value: unknown }[]>`
      select value from config where key = 'skills.charges_by_kind.approved'`;
    await page.goto("/skill-sets/approve");
    const grades = page.getByRole("navigation", { name: "Grade" });
    await expect(grades.getByRole("link", { name: /^Every grade\s*4$/ })).toHaveAttribute("aria-current", "page");
    await grades.getByRole("link", { name: /^Grade 2\s*2$/ }).click();
    await expect(page).toHaveURL(/[?&]grade=G2(&|$)/);
    await expectRows(page, ["ADD.2D2D", "SUB.2D2D"]);

    // a topic, under every grade: only its skills
    await grades.getByRole("link", { name: /^Every grade/ }).click();
    await expectRows(page, DRAFTS);
    await page.getByLabel("Topic").selectOption({ label: "Division (1)" });
    await page.getByRole("button", { name: "Show" }).click();
    await expect(page).toHaveURL(/[?&]topic=DIV(&|$)/);
    await expectRows(page, ["DIV.3D1D"]);
    await page.getByLabel("Topic").selectOption({ value: "" });
    await page.getByLabel("Taught").selectOption({ label: "Not taught yet (1)" });
    await page.getByRole("button", { name: "Show" }).click();
    await expect(page).toHaveURL(/[?&]taught=no(&|$)/);
    await expectRows(page, ["DIV.3D1D"]);

    // Grade 2's two, approved together: the other two and the mistake table still wait
    await page.goto("/skill-sets/approve?grade=G2");
    await expectRows(page, ["ADD.2D2D", "SUB.2D2D"]);
    await page.getByRole("button", { name: `Approve these 2 skills as written, as ${TEST_STAFF.name}` }).click();
    await expect(page).toHaveURL(/\/skill-sets\/approve\?grade=G2&approved=2$/);
    await expect(page.getByRole("status").filter({ hasText: "Approved, in your name. 2 still wait." })).toBeVisible();
    const after = await sql<{ code: string; status: string; ratified_by: string | null }[]>`
      select code, status, ratified_by from skill where code = any(${DRAFTS}) order by code`;
    expect(after).toEqual([
      { code: "ADD.1D1D", status: "draft", ratified_by: null },
      { code: "ADD.2D2D", status: "ratified", ratified_by: TEST_STAFF.name },
      { code: "DIV.3D1D", status: "draft", ratified_by: null },
      { code: "SUB.2D2D", status: "ratified", ratified_by: TEST_STAFF.name },
    ]);
    const [{ value: tableAfter }] = await sql<{ value: unknown }[]>`
      select value from config where key = 'skills.charges_by_kind.approved'`;
    expect(tableAfter, "approving some skills never approves the mistake table").toEqual(tableBefore);
  });
});
