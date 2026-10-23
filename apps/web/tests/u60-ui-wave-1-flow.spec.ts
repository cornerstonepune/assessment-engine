/**
 * UI wave 1 — an educator's week, walked page by page at 1440 px (goals/ui-wave-1.yaml). Nimish, 23 Oct 2026:
 * "just go ahead and build the whole flow and get it live properly - only when I see it and interact with it on the
 * dashboard can I suggest changes."
 *
 * Today → Assessments (upload box on top, one count per assessment, filters) → Papers to approve → Print and give →
 * Upload papers → Check answers → Marking (the papers read) → Class results → the Assessment card → Curriculum (Maths,
 * then English) → Staff and School. On every page: each table's head sits over its columns, a status is an icon and a
 * word, a filter row is there, every row opens something, and nothing says "This page could not load". A class of the
 * test's own, three children and four papers, is kept (evidence is append-only), as the other specs' are.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek } from "../lib/week";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "WV1-CLASS";
const THIS = isoWeek();
const QR = { asha: "CSF10A01", bina: "CSF10B02", chetan: "CSF10C03", spare: "CSF10D04" };
let kids: Record<string, string> = {};

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan", "Dev"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const ws = await sql<{ id: string; item_ids: string[]; skill: string }[]>`
    select id, item_ids, skill_set_code as skill from sheet_template
    where source = 'library' and retired_at is null and band = 'G2'
      and skill_set_code = (select skill_set_code from sheet_template where source = 'library' and retired_at is null
                            and band = 'G2' and difficulty = 'Hard' order by skill_set_code limit 1)
      and difficulty in ('Medium', 'Hard')
    order by difficulty = 'Hard' desc, code limit 4`;
  if (ws.length < 4) throw new Error(`the flow needs four library worksheets of one Grade 2 skill set; the database has ${ws.length}`);
  const paper = (qr: string, w: string, child: string | null, status: string) => sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${tenant}, ${qr}, ${w}, ${child}, ${THIS}, ${SECTION}, 'assessment', ${status},
           ${status === "new" ? null : "wv1"}, ${status === "new" ? null : sql`now()`}
    where not exists (select 1 from sheet_instance where qr_code = ${qr})`;
  await paper(QR.asha, ws[0].id, kids.Asha, "printed");
  await paper(QR.bina, ws[1].id, kids.Bina, "printed");
  await paper(QR.chetan, ws[2].id, kids.Chetan, "new");
  await paper(QR.spare, ws[3].id, null, "new");
  // Bina's copy is read: one answer is right, one waits for a person to say what the child wrote
  await aReadPaper(sql, {
    qr: QR.bina,
    child: kids.Bina,
    template: ws[1].id,
    items: ws[1].item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  });
  await sql`delete from prescription where child_id in ${sql(Object.values(kids))} and week = ${THIS}`;
  const sheet = async (qr: string) => (await sql<{ id: string }[]>`select id from sheet_instance where qr_code = ${qr}`)[0].id;
  for (const [who, level, qr] of [
    ["Asha", "Hard", QR.asha],
    ["Bina", "Hard", QR.bina],
    ["Chetan", "Medium", QR.chetan],
    ["Dev", "Hard", null],
  ] as const) {
    await sql`
      insert into prescription (tenant_id, child_id, week, kind, skill_set_code, difficulty, rule_fired, strand, sheet_instance_id, no_paper, created_at)
      values (${tenant}, ${kids[who]}, ${THIS}, 'assessment', ${ws[0].skill}, ${level}, 'band_default', 'NUM',
              ${qr ? await sheet(qr) : null}, ${qr ? null : "has sat every worksheet at Hard (4)"}, now() - interval '1 day')`;
  }
});
test.afterAll(async () => {
  await sql.end();
});

/** The page opened, with nothing broken on it. */
async function open(page: Page, path: string, title: RegExp) {
  const res = await page.goto(path);
  expect(res?.status(), `${path} answers`).toBeLessThan(400);
  await expect(page.getByRole("heading", { level: 1 }).first(), `${path}: its title`).toHaveText(title);
  await expect(page.getByText("This page could not load"), `${path} loads`).toHaveCount(0);
}

/** Every table on the page: the head over its columns, and a way into every row. */
async function tablesRead(page: Page, path: string) {
  const tables = page.locator(".data-table table");
  const n = await tables.count();
  expect(n, `${path}: a table`).toBeGreaterThan(0);
  for (let t = 0; t < n; t++) {
    const table = tables.nth(t);
    if (!(await table.isVisible())) continue; // behind a fold the educator has not opened
    const name = `${path} “${await table.getAttribute("aria-label")}”`;
    const heads = table.locator("thead th");
    const body = table.locator("tbody tr:not(.under)");
    const rows = await body.count();
    if (rows === 0) continue;
    const first = body.first().locator("td");
    expect(await first.count(), `${name} table ${t}: a cell under each heading`).toBe(await heads.count());
    // a heading is never split inside a word: one wider than its column would overflow it
    const cramped = await heads.evaluateAll((hs) => hs.filter((h) => h.scrollWidth > h.clientWidth + 1).map((h) => h.textContent));
    expect(cramped, `${name}: headings that do not fit their column`).toEqual([]);
    for (let c = 0; c < (await heads.count()); c++) {
      const h = await heads.nth(c).boundingBox();
      const d = await first.nth(c).boundingBox();
      if (!h || !d) continue; // a column hidden on this width has neither
      expect(Math.abs(h.x - d.x), `${name} table ${t} column ${c}: heading and cell start together (${h.x},${h.width} vs ${d.x},${d.width})`).toBeLessThan(2);
      expect(Math.abs(h.width - d.width), `${name} table ${t} column ${c}: heading and cell are as wide`).toBeLessThan(2);
    }
    for (let r = 0; r < rows; r++) {
      const row = body.nth(r);
      expect(await row.locator("a[href], button, input, select").count(), `${name} table ${t} row ${r}: opens something`).toBeGreaterThan(0);
    }
  }
}

/** A status is an icon and a word. */
async function statusesSaid(page: Page, path: string) {
  const chips = page.locator("[data-status]:visible");
  const n = Math.min(await chips.count(), 40);
  for (let i = 0; i < n; i++) {
    const chip = chips.nth(i);
    await expect(chip.locator("svg[data-icon]"), `${path}: a status has its icon`).toHaveCount(1);
    expect(((await chip.innerText()) ?? "").trim().length, `${path}: a status has its word`).toBeGreaterThan(1);
  }
}

async function wholePage(page: Page, path: string, title: RegExp, { filter = true, chips = false } = {}) {
  await open(page, path, title);
  await tablesRead(page, path);
  if (filter) await expect(page.locator("[data-filterbar]").first(), `${path}: a filter row`).toBeVisible();
  if (chips) {
    expect(await page.locator("[data-status]:visible").count(), `${path}: a status somewhere`).toBeGreaterThan(0);
    await statusesSaid(page, path);
  }
}

test("Today opens, and its first action leads on", async ({ page }) => {
  await open(page, "/today", /Today/);
  await expect(page.locator("[data-ux=action] a, [data-ux=action] button").first()).toBeVisible();
  await tablesRead(page, "/today");
  await expect(page.locator("[data-filterbar]").first()).toBeVisible();
});

test("Assessments: the upload box on top, one count per assessment, filters", async ({ page }) => {
  await wholePage(page, "/papers", /Assessments/, { chips: true });
  const box = await page.getByText(/upload|choose a file|drop/i).first().boundingBox();
  const table = await page.locator(".data-table").first().boundingBox();
  expect(box && table && box.y < table.y, "the upload box is above the table").toBe(true);
  // the filter row chooses the class; one count per assessment: the week's is one row, not one per child
  await page.locator("[data-filterbar] select[name=class]").selectOption(SECTION);
  await expect(page).toHaveURL(new RegExp(`class=${SECTION}`));
  await expect(page.locator("tr[data-assessment]")).toHaveCount(1);
  await page.getByRole("link", { name: /clear/i }).first().click();
  await expect(page).not.toHaveURL(/class=/);
});

test("Papers to approve: one table, the pack's approval the one action", async ({ page }) => {
  await wholePage(page, `/papers/approve?section=${SECTION}&week=${THIS}&kind=assessment`, /Papers to approve/, { chips: true });
  await expect(page.locator("[data-ux=action] button")).toBeVisible();
  await expect(page.locator("[data-ux=next]")).toHaveAttribute("href", "/papers");
});

test("Print and give: the classes as a table, a class's children as a table", async ({ page }) => {
  await wholePage(page, "/make", /Home assessments/, { chips: true });
  await wholePage(page, `/make/${SECTION}`, /./, { chips: true });
});

test("Upload papers, Check answers, Marking", async ({ page }) => {
  await wholePage(page, "/capture", /Upload papers/, { chips: true });
  await wholePage(page, "/capture/check", /Check answers/, { chips: true });
  // Marking: the papers read, by class, and one child's
  await page.goto("/capture?view=class");
  await expect(page.getByText("This page could not load")).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Bina/ }).first()).toBeVisible();
});

test("Class results, its class and a child", async ({ page }) => {
  await wholePage(page, "/growth", /Class results/, { chips: true });
  await page.goto(`/growth?class=${SECTION}`);
  const child = page.getByRole("link", { name: /Bina/ }).first();
  await expect(child).toBeVisible();
  await child.click();
  await expect(page.getByText("This page could not load")).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1 }).first()).toContainText("Bina");
});

test("the Assessment card, opened from its row", async ({ page }) => {
  await page.goto(`/papers?class=${SECTION}`);
  await page.locator("tr[data-assessment]").getByRole("link").first().click();
  const card = page.getByRole("link", { name: /Open its card/ });
  await expect(card).toBeVisible();
  await card.click();
  await expect(page.getByText("This page could not load")).toHaveCount(0);
  await expect(page.getByTestId("stage")).toHaveText(/its card/i);
  await tablesRead(page, "card");
  await expect(page.locator("[data-filterbar]").first()).toBeVisible();
  await statusesSaid(page, "card");
});

test("Curriculum, Maths then English, and Staff and School", async ({ page }) => {
  await wholePage(page, "/", /Curriculum/, { chips: true });
  const maths = await page.locator(".data-table tbody tr").count();
  expect(maths).toBeGreaterThan(0);
  // the filter row says the subject too: its rows are that subject's alone
  await page.locator("[data-filterbar] select[name=subject]").selectOption("English");
  await expect(page).toHaveURL(/subject=English/);
  const column = (await page.locator(".data-table thead th").allInnerTexts()).findIndex((h) => h.trim().toLowerCase() === "subject");
  expect(column, "the table has a Subject column").toBeGreaterThanOrEqual(0);
  const cells = await page.locator(`.data-table tbody tr:not(.under) td:nth-child(${column + 1})`).allInnerTexts();
  expect(cells.length).toBeGreaterThan(0);
  for (const cell of cells) expect(cell.trim()).toBe("English");
  await page.locator("#bar-subject").selectOption({ label: "English" });
  await expect(page.getByRole("heading", { level: 1 }).first()).toHaveText(/Curriculum/);
  await expect(page.getByText("This page could not load")).toHaveCount(0);
  await tablesRead(page, "/ (English)");
  await page.locator("#bar-subject").selectOption({ label: "Maths" });
  await wholePage(page, "/staff", /Staff/, { filter: false });
  await wholePage(page, "/school", /School/, { filter: false });
});

test("the flow is one chain: each page's next step opens the following page", async ({ page }) => {
  const chain = ["/today", "/taught", "/papers/approve", "/papers", "/capture", "/capture/check", "/growth"];
  for (const path of chain) {
    await page.goto(path);
    await expect(page.getByText("This page could not load"), path).toHaveCount(0);
    const next = page.locator("[data-ux=next]");
    await expect(next, `${path}: one next step, never a dead end`).toHaveCount(1);
    const href = (await next.getAttribute("href"))!;
    const to = new URL(href, page.url());
    // the queue of answers to check goes on to the next answer, on the same page; every other page goes to another
    expect(`${to.pathname}${to.search}`, `${path}: its next step is somewhere else`).not.toBe(path);
    const res = await page.goto(href);
    expect(res?.status(), `${path} → ${href}`).toBeLessThan(400);
    await expect(page.getByText("This page could not load"), href).toHaveCount(0);
    await expect(page.getByRole("heading", { level: 1 }).first(), `${path} → ${href}: a page with a title`).toBeVisible();
  }
});
