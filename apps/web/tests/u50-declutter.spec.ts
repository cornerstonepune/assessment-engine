/**
 * U50 — the educator's pages, decluttered (goals/ux10-declutter.yaml). Nimish, 2026-10-22, on the live site: "Look at
 * the clutter"; "The current frontend is extremely confusing to me ... make it much, much cleaner."
 *
 * An educator of two Grade 2 classes of the test's own, made once and kept (evidence is append-only):
 * - U50-BUSY: Asha, who needs help (four wrong answers taking the smaller digit from the larger, two right) and has two
 *   answers waiting for a person; Bina, with nothing yet;
 * - U50-QUIET: Cara and Dev, with nothing yet — so nothing in their table has a number to show.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const BUSY = "U50-BUSY";
const QUIET = "U50-QUIET";
const EDUCATOR = { email: "u50-educator@cornerstone.test", name: "U50 Educator", role: "educator", classes: [BUSY, QUIET] };
const PASSWORD = "u50-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
let kids: Record<string, string> = {};

test.beforeAll(async () => {
  kids = await aClass(sql, BUSY, "G2", ["Asha", "Bina"]);
  await aClass(sql, QUIET, "G2", ["Cara", "Dev"]);
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${kids.Asha}`;
  if (!n) {
    const answers: boolean[] = [false, false, false, false, true, true];
    for (const right of answers) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${kids.Asha}, 'NUM.OPS.02', 'R24', ${right}, ${right ? [] : ["M_SMALL_FROM_LARGE"]}, 'item',
                now(), 'u50')`;
    }
    await sql`select rebuild_child_skill_state(${kids.Asha}::uuid)`;
  }
  const [w] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where source = 'library' and retired_at is null and band = 'G2'
    order by code limit 1`;
  await aReadPaper(sql, {
    qr: "U50-ASHA",
    child: kids.Asha,
    template: w.id,
    items: w.item_ids.slice(0, 3),
    reads: [{ status: "needs_teacher", read: "41" }, { status: "needs_teacher", read: "7" }, { status: "correct", read: "12" }],
  });
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

const group = (page: Page, section: string) => page.locator("details[data-class]").filter({ has: page.locator(`summary:has-text("${section}")`) });

test("Children leads with the children who need the educator, as a short list", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth");
  const lead = page.getByRole("region", { name: "Need you" });
  await expect(lead).toBeVisible();
  // the child who needs help and has answers waiting is on it, and links to the child; a child with nothing is not
  await expect(lead.getByRole("link", { name: /Asha/ })).toHaveAttribute("href", `/growth/${kids.Asha}`);
  await expect(lead).not.toContainText("Bina");
  await expect(lead).not.toContainText("Cara");
  expect(await lead.getByRole("listitem").count(), "a short list").toBeLessThanOrEqual(8);
  // and it comes before the classes
  const [leadY, classY] = await Promise.all([lead.boundingBox(), group(page, BUSY).boundingBox()]);
  expect(leadY!.y).toBeLessThan(classY!.y);
  await page.context().close();
});

test("a class's table holds only the columns that have something in them", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth");
  // a class with nothing to show: the child, and the roll number, and nothing else
  const quiet = page.getByRole("table", { name: `${QUIET}: its children` });
  await expect(quiet).toBeVisible();
  expect((await quiet.getByRole("columnheader").allTextContents()).map((h) => h.trim())).toEqual(["Roll", "Child"]);
  // a class with something: every column it shows has a number, a name or a pill in some row, and no cell is a dash or a nought
  const busy = page.getByRole("table", { name: `${BUSY}: its children` });
  await expect(busy).toBeVisible();
  const heads = (await busy.getByRole("columnheader").allTextContents()).map((h) => h.trim());
  expect(heads.map((h) => h.replace(/\s*▾$/, ""))).toEqual(expect.arrayContaining(["Roll", "Child", "Needs help on", "Needs help", "Waiting on you"]));
  const rows = await busy.locator("tbody tr").all();
  for (let c = 0; c < heads.length; c++) {
    const cells = await Promise.all(rows.map(async (r) => (await r.locator("td").nth(c).innerText()).trim()));
    expect(cells.some((t) => t !== "" && t !== "0" && t !== "—"), `${heads[c]} has something in it`).toBe(true);
    expect(cells.filter((t) => t === "0" || t === "—"), `${heads[c]}: no nought or dash`).toEqual([]);
  }
  await page.context().close();
});

test("Children has no topic chips and no second box to find a child; all skills is a quiet link", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/growth");
  await expect(page.getByRole("navigation", { name: "Topic" })).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("textbox")).toHaveCount(0);
  const all = page.getByRole("link", { name: `${BUSY} against every skill →` });
  await expect(all).toBeVisible();
  // quiet: small type, never a button or a chip
  expect(await all.evaluate((a) => parseFloat(getComputedStyle(a).fontSize))).toBeLessThanOrEqual(12.5);
  await expect(all).not.toHaveClass(/chip|btn/);
  // the long explanation and the key to the colours are put away behind a link, not shown
  const details = page.getByRole("main").locator("details", { hasText: "Details" }).last();
  await expect(details).not.toHaveAttribute("open", "");
  await expect(details.getByText(/From checked papers only/)).toBeHidden();
  await page.context().close();
});

test("in the menu only Today carries a count", async ({ browser }) => {
  const page = await asEducator(browser);
  for (const path of ["/today", "/", "/growth"]) {
    await page.goto(path);
    const menu = page.getByRole("navigation", { name: "Sections" });
    // Asha's waiting answers make Assessments and Today non-zero, so a count elsewhere would show
    await expect(menu.getByRole("link", { name: /^Today/ }).getByTestId("waiting")).toBeVisible();
    for (const tab of ["Curriculum", "Assessments", "Children"]) {
      await expect(menu.getByRole("link", { name: new RegExp(`^${tab}\\b`) }).getByTestId("waiting"), `${tab} on ${path}`).toHaveCount(0);
    }
    await expect(menu.getByTestId("waiting")).toHaveCount(1);
  }
  await page.context().close();
});

test("Curriculum shows grades, topics and skills with what each level asks; the bank's counts wait behind Question bank details", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/");
  const table = page.getByRole("table", { name: "The curriculum, grade by grade" });
  await expect(table.getByRole("columnheader")).toHaveCount(1);
  await page.getByRole("button", { name: "Open everything" }).click();
  // a skill's row says what each level asks, in the school's words (the skill's own sentences)
  const skill = table.locator("tbody tr[data-depth='3']").first();
  await expect(skill.getByRole("list")).toBeVisible();
  await expect(skill.getByRole("listitem").first()).toContainText(/^(Easy|Medium|Hard|Advance) · \S+/);
  // none of the bank's counts, nor its other doors, nor the word the team uses for its map
  const main = page.getByRole("main");
  for (const word of ["Questions", "Worksheets", "Children assessed", "taxonomy", "Every question in the bank"]) {
    await expect(main.getByText(word, { exact: false }), word).toHaveCount(0);
  }
  // one link puts them there
  await page.getByRole("link", { name: "Question bank details" }).click();
  await expect(page).toHaveURL(/details=1/);
  await expect(table.getByRole("columnheader", { name: "Questions" })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Worksheets" })).toBeVisible();
  await expect(main.getByRole("link", { name: "Every question in the bank" })).toBeVisible();
  await expect(main.getByRole("link", { name: "Every case, with its worksheets" })).toBeVisible();
  // a topic not taught yet is a word on its row, and the two big sections are gone
  await expect(page.getByRole("region", { name: "Not taught yet" })).toBeHidden();
  await page.context().close();
});

test("under a page's title there is one line, never a paragraph", async ({ browser }) => {
  const page = await asEducator(browser);
  for (const path of ["/today", "/", "/growth"]) {
    await page.goto(path);
    const sub = page.locator("header p");
    expect(await sub.count(), `${path}: at most one line under the title`).toBeLessThanOrEqual(1);
    for (const t of await sub.allInnerTexts()) expect(t.length, `${path}: ${t}`).toBeLessThanOrEqual(140);
    // and no paragraph anywhere on the two decluttered pages is a paragraph of explanation
    if (path !== "/today") {
      for (const p of await page.getByRole("main").locator("p:visible").all()) {
        expect((await p.innerText()).length, `${path} has a paragraph over 140 characters`).toBeLessThanOrEqual(140);
      }
    }
  }
  await page.context().close();
});
