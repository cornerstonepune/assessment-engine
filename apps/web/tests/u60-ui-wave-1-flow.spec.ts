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
import { createHmac } from "node:crypto";
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

// An educator mapped to one class and one subject (goals/nav_teacher_scope_and_todo.yaml): signed in as the site signs one in.
const EDUCATOR = { email: "wv1-educator@cornerstone.test", name: "Wave Educator", role: "educator", classes: [SECTION], subjects: ["NUM"] };
test.beforeAll(async () => {
  await sql`
    update config set value = value || ${sql.json([EDUCATOR])}
    where key = 'app.staff' and not value @> ${sql.json([{ email: EDUCATOR.email }])}`;
});
async function asEducator(browser: import("@playwright/test").Browser) {
  const body = `${Buffer.from(EDUCATOR.email).toString("base64url")}.${Date.now() + 3_600_000}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  const context = await browser.newContext({ baseURL: "http://localhost:3100", viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
  return { context, page: await context.newPage() };
}

const GROUP_NAMES = ["What needs doing", "Teaching", "Assessments", "Results", "Setup"];

/** The top navigation: the mark, the five groups on one bar, a menu button, and no sidebar. */
async function theTopBar(page: Page) {
  await expect(page.locator("header img[data-brand-mark]"), "the new logo mark").toBeVisible();
  expect(await page.locator("aside").count(), "no left sidebar").toBe(0);
  const groups = page.getByRole("navigation", { name: "Sections" });
  expect((await groups.getByRole("link").allInnerTexts()).map((n) => n.replace(/\s*\d[\d,]*$/, "").trim())).toEqual(GROUP_NAMES);
  const bar = await groups.boundingBox();
  expect(bar && bar.y < 60, "the groups are in the bar at the top").toBe(true);
  const main = await page.getByRole("main").boundingBox();
  expect(main && main.x < 100, "the content starts at the left, no gutter for a menu").toBe(true);
  await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
}

test("an educator with one class and one subject: top menu, only hers, no Class or Subject boxes, no approve-all", async ({ browser }) => {
  const { context, page } = await asEducator(browser);
  await open(page, "/today", /What needs doing/);
  await theTopBar(page);
  await expect(page.locator("#bar-subject, #bar-class, [data-viewing]"), "no universal Class or Subject selector").toHaveCount(0);
  // the menu button opens every group with its pages, and sign out
  await page.getByRole("button", { name: "Menu" }).click();
  const panel = page.getByRole("dialog", { name: "Menu" });
  for (const name of ["Papers to approve", "Check answers", "Class results", "Skills to approve", "Staff"]) await expect(panel.getByRole("link", { name }), name).toBeVisible();
  await expect(panel.getByRole("button", { name: "Sign out" })).toBeVisible();
  await page.keyboard.press("Escape");
  // What needs doing: a table, red/amber/green rows, one action on each row that opens that item
  const rows = page.locator(".data-table tbody tr[data-kind]");
  expect(await rows.count(), "rows of tasks").toBeGreaterThan(0);
  for (const row of await rows.all()) {
    await expect(row.locator("[data-status]"), "a priority chip with its icon").toHaveCount(1);
    await expect(row.locator("a[data-action]"), "one action").toHaveCount(1);
  }
  expect(await page.locator("tr[data-state=doNow]").count(), "a red row first").toBeGreaterThan(0);
  expect(await page.locator("tr[data-state=doNow]").first().evaluate((el) => el.closest("table")!.querySelector("tbody tr")?.getAttribute("data-state"))).toBe("doNow");
  await expect(page.getByRole("button", { name: /approve (all|them|these|every)/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /approve (all|them|these|every)/i })).toHaveCount(0);
  // only her class: no row names another class's paper
  const where = await page.locator("td[data-label=Where]").allInnerTexts();
  expect(where.filter((w) => /·\s*\d[A-Z]\b/.test(w) && !w.includes(SECTION)), "rows of another class").toEqual([]);
  const first = rows.first().locator("a[data-action]");
  const href = (await first.getAttribute("href"))!;
  await first.click();
  await expect(page).toHaveURL(new RegExp(href.split("?")[0].replace(/[/]/g, "\\/")));
  await expect(page.getByText("This page could not load")).toHaveCount(0);
  await context.close();
});

test("an educator's Teaching: her subject, topics as a table with the topic flow, no skill approval", async ({ browser }) => {
  const { context, page } = await asEducator(browser);
  await open(page, "/taught", /Teaching/);
  await expect(page.getByRole("navigation", { name: "Subjects" }), "one subject, so no subject tabs").toHaveCount(0);
  await tablesRead(page, "/taught");
  expect(await page.locator("button, a").filter({ hasText: /approve/i }).count(), "no skill-approval control on Teaching").toBe(0);
  // her class's flow on the topic her papers are of: skills ready, a baseline given, home assessments
  const flow = page.locator(`[data-flow="${SECTION}"]`).first();
  await expect(flow).toBeVisible();
  await expect(flow).toContainText("Baseline");
  await expect(flow).toContainText("Home assessments");
  await expect(flow.locator("[data-step]")).toHaveCount(4);
  // one action per row, in the row: say it is taught
  const row = page.locator("tr[data-topic]").filter({ has: page.locator(`[data-flow="${SECTION}"]`) }).first();
  await expect(row.getByRole("button", { name: /Mark as taught|Not taught after all/ })).toHaveCount(1);
  await context.close();
});

test("an admin: the same top menu and a Viewing control, both subjects on Teaching", async ({ page }) => {
  await open(page, "/today", /What needs doing/);
  await theTopBar(page);
  await expect(page.locator("[data-viewing] summary")).toContainText("Viewing:");
  await page.locator("[data-viewing] summary").click();
  await expect(page.locator("#bar-subject")).toBeVisible();
  await expect(page.locator("#bar-class")).toBeVisible();
  await open(page, "/taught", /Teaching/);
  expect((await page.getByRole("navigation", { name: "Subjects" }).getByRole("link").allInnerTexts()).sort()).toEqual(["English", "Maths"]);
  // a group's other pages are tabs, not more items on the bar
  await page.goto("/papers");
  await expect(page.getByRole("navigation", { name: "Pages in this section" }).getByRole("link")).toHaveText(["Assessments", "Papers to approve", "Upload papers", "Check answers"]);
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

/** The Viewing control (a coordinator's): open it, choose the subject. */
async function viewSubject(page: Page, label: string) {
  await page.waitForLoadState("networkidle");
  await page.locator("[data-viewing]").evaluate((el) => ((el as HTMLDetailsElement).open = true));
  await expect(page.locator("#bar-subject")).toBeVisible();
  await Promise.all([page.waitForResponse((r) => r.request().method() === "POST"), page.locator("#bar-subject").selectOption({ label })]);
  await page.waitForLoadState("networkidle");
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

test("What needs doing opens, and its first action leads on", async ({ page }) => {
  await open(page, "/today", /What needs doing/);
  await expect(page.locator("[data-ux=action] a, [data-ux=action] button").first()).toBeVisible();
  await tablesRead(page, "/today");
  await expect(page.locator("[data-filterbar]").first()).toBeVisible();
});

test("Assessments: the two blocks on top, one row per assessment, filters", async ({ page }) => {
  await wholePage(page, "/papers", /Assessments/, { chips: true });
  const box = await page.getByRole("region", { name: "Read an assessment" }).boundingBox();
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
  await page.goto(`/capture?by=child&class=${SECTION}`);
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
  await expect(page.getByRole("columnheader", { name: "Subject" })).toBeVisible();
  const column = (await page.locator(".data-table thead th").allInnerTexts()).findIndex((h) => h.trim().toLowerCase() === "subject");
  expect(column, "the table has a Subject column").toBeGreaterThanOrEqual(0);
  const cells = await page.locator(`.data-table tbody tr:not(.under) td:nth-child(${column + 1})`).allInnerTexts();
  expect(cells.length).toBeGreaterThan(0);
  for (const cell of cells) expect(cell.trim()).toBe("English");
  await viewSubject(page, "English");
  await expect(page.getByRole("heading", { level: 1 }).first()).toHaveText(/Curriculum/);
  await expect(page.getByText("This page could not load")).toHaveCount(0);
  await tablesRead(page, "/ (English)");
  await viewSubject(page, "Maths");
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
