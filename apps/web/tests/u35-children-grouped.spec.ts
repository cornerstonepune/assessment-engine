/**
 * U35 — Children grouped by class (goals/ux3-children-grouped.yaml). Nimish, 2026-10-15, on live's Children page: "Most
 * of the pages just have a long list for no reason. All these things should be expandable and collapsible. They should
 * have the right set of columns which are important. It should be teacher-specific and all of those things."
 *
 * Two Grade 2 classes of the test's own, one the educator's, made once and kept (evidence is append-only):
 * - Asha needs help: four wrong answers taking the smaller digit from the larger, two right; her report was written
 *   before those answers, so it is out of date; two of her answers wait for a person;
 * - Bina has nothing yet;
 * - Chetan is secure on one skill, his report approved;
 * - Kavi is in the other class.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Locator, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U35-MINE";
const OTHER = "U35-OTHER";
const EDUCATOR = { email: "u35-educator@cornerstone.test", name: "U35 Educator", role: "educator", classes: [MINE] };
const PASSWORD = "u35-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
// the columns with something in them in this class: nobody is practising, so that column is left out (goals/ux10-declutter.yaml)
const COLUMNS = ["Roll", "Child", "Needs help on", "Needs help", "Secure", "Waiting on you", "Parent report"];
let kids: Record<string, string> = {};
let mistake = "";

test.beforeAll(async () => {
  kids = await aClass(sql, MINE, "G2", ["Asha", "Bina", "Chetan"]);
  await aClass(sql, OTHER, "G2", ["Kavi"]);
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${kids.Asha}`;
  if (!n) {
    // Asha's report first, then the answers it no longer covers
    await sql`insert into parent_note (tenant_id, child_id, week, body, created_at)
              values (${tenant}, ${kids.Asha}, 'U35', '{"facts": {}, "draft": {}}', now() - interval '2 days')`;
    const answers: [string, boolean, string[]][] = [
      ...Array<[string, boolean, string[]]>(4).fill([kids.Asha, false, ["M_SMALL_FROM_LARGE"]]),
      ...Array<[string, boolean, string[]]>(2).fill([kids.Asha, true, []]),
      ...Array<[string, boolean, string[]]>(6).fill([kids.Chetan, true, []]),
    ];
    for (const [child, right, mistakes] of answers) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${child}, 'NUM.OPS.02', ${child === kids.Asha ? "R24" : "R23"}, ${right}, ${mistakes}, 'item',
                now(), 'u35')`;
    }
    for (const child of [kids.Asha, kids.Chetan]) await sql`select rebuild_child_skill_state(${child}::uuid)`;
    await sql`insert into parent_note (tenant_id, child_id, week, body, approved_by, created_at)
              values (${tenant}, ${kids.Chetan}, 'U35', '{"facts": {}, "draft": {}}', 'u35', now() + interval '1 minute')`;
  }
  // two of Asha's answers wait for a person, on a worksheet the library holds
  const [w] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where source = 'library' and retired_at is null and band = 'G2'
    order by code limit 1`;
  await aReadPaper(sql, {
    qr: "U35-ASHA",
    child: kids.Asha,
    template: w.id,
    items: w.item_ids.slice(0, 3),
    reads: [{ status: "needs_teacher", read: "41" }, { status: "needs_teacher", read: "7" }, { status: "correct", read: "12" }],
  });
  [{ name: mistake }] = await sql<{ name: string }[]>`select mistake_name('M_SMALL_FROM_LARGE', 'NUM.OPS.02') as name`;
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

/** A class's group on the page: a disclosure whose summary starts with the class. */
const group = (page: Page, section: string) => page.locator("details[data-class]").filter({ has: page.locator(`summary:has-text("${section}")`) });
const rows = (g: Locator) => g.locator("tbody tr");

test("an educator sees each of their classes open, and no other", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth");
  const mine = group(page, MINE);
  await expect(mine).toHaveCount(1);
  await expect(mine).toHaveAttribute("open", "");
  await expect(rows(mine)).toHaveCount(3);
  await expect(page.locator("details[data-class]")).toHaveCount(1);
  await expect(page.getByRole("main")).not.toContainText(OTHER);
  await expect(page.getByRole("main")).not.toContainText("Kavi");
  await page.context().close();
});

test("the coordinator sees every class closed under its grade, says what waits in each, and opens it in place", async ({ page }) => {
  await page.goto("/growth");
  const mine = group(page, MINE);
  await expect(mine).toHaveCount(1);
  await expect(group(page, OTHER)).toHaveCount(1);
  await expect(mine).not.toHaveAttribute("open", "");
  await expect(rows(mine).first()).toBeHidden();
  // its one line: three children, one needing help, Asha's two answers waiting, her report out of date
  await expect(mine.locator("summary")).toContainText(/3 children\b.*1 needs? help\b.*2 answers waiting\b.*1 parent report waiting/);
  await expect(mine.locator("xpath=ancestor::section[1]")).toContainText("Grade 2");
  await mine.locator("summary").click();
  await expect(mine).toHaveAttribute("open", "");
  await expect(rows(mine)).toHaveCount(3);
});

test("a class's table has the columns that matter, children who need help first", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth");
  const mine = group(page, MINE);
  // the sorted column carries its marker
  await expect(mine.locator("thead th")).toHaveText(COLUMNS.map((c) => new RegExp(`^${c}( ▾)?$`)));
  // Asha first: she needs help; then the roll
  await expect(rows(mine).first()).toHaveAttribute("data-child", kids.Asha);
  const asha = rows(mine).first().locator("td");
  await expect(asha.nth(1)).toHaveText("Asha");
  await expect(asha.nth(2)).toContainText(mistake);
  await expect(asha.nth(3)).toHaveText("1");
  await expect(asha.nth(5)).toHaveText("2");
  await expect(asha.nth(6)).toContainText(/out of date/i);
  // a report already approved is nobody's work: the cell is empty
  const chetan = mine.locator(`tbody tr[data-child="${kids.Chetan}"] td`);
  await expect(chetan.nth(4)).toHaveText("1");
  await expect(chetan.nth(6)).toHaveText(/^\s*$/);
  await page.context().close();
});

test("the colour key is one line, and at 400 px nothing scrolls sideways", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.setViewportSize({ width: 400, height: 860 });
  await page.goto("/growth");
  // the key is put away behind "Details" (goals/ux10-declutter.yaml); read once the page has streamed in
  await page.getByText("Details", { exact: true }).click();
  const key = page.locator("details[data-colour-key]");
  await expect(key.locator("summary")).toBeVisible();
  await expect(key).toHaveCount(1);
  await expect(key).not.toHaveAttribute("open", "");
  expect((await key.locator("summary").boundingBox())!.height).toBeLessThan(40);
  await key.locator("summary").click();
  await expect(key.locator("[data-rag]").first()).toBeVisible();

  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(wide, "the page is no wider than the phone").toBeLessThanOrEqual(400);
  const mine = group(page, MINE);
  const row = rows(mine).first();
  for (const cell of [row.locator("td").nth(1), row.locator("td").nth(2)]) {
    const box = (await cell.boundingBox())!;
    expect(box.x + box.width, "the child and what they need help on are on screen").toBeLessThanOrEqual(400);
  }
  await page.context().close();
});
