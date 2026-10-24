/**
 * The Assessments page at 1440 px (goals/asm_assessments_page.yaml). Nimish, 24 Oct 2026: "This assessment page can be
 * much better formatted... two nice blocks side by side... a very proper list of the last 5, last 7 assessments... we
 * should ideally have the ability to name the assessment. We should not use these file names... Then we have this 4.
 * There is no sequence of anything... There is nothing hidden from the system."
 *
 * A class of the test's own: a class assessment (one child's paper printed, one not printed, one read with an answer
 * waiting for a person) and a home assessment waiting for approval; one file read that belongs to the class assessment
 * and one that belongs to none. Evidence is append-only, so the rows are kept, as the other specs' are.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek } from "../lib/week";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "ASM-CLASS";
const THIS = isoWeek();
const QR = { asha: "CSA5A001", bina: "CSA5A002", chetan: "CSA5A003", home: "CSA5A004" };
let skillName = "";

test.beforeAll(async () => {
  const kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan", "Dev"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const ws = await sql<{ id: string; item_ids: string[]; skill: string }[]>`
    select id, item_ids, skill_set_code as skill from sheet_template
    where source = 'library' and retired_at is null and band = 'G2'
      and skill_set_code = (select skill_set_code from sheet_template where source = 'library' and retired_at is null
                            and band = 'G2' and difficulty = 'Hard' order by skill_set_code limit 1)
      and difficulty in ('Medium', 'Hard')
    order by difficulty = 'Hard' desc, code limit 4`;
  if (ws.length < 4) throw new Error(`needs four library worksheets of one Grade 2 skill set; the database has ${ws.length}`);
  [{ name: skillName }] = await sql<{ name: string }[]>`select name from skill where code = ${ws[0].skill}`;
  const paper = (qr: string, w: string, child: string, status: string, kind: string) => sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${tenant}, ${qr}, ${w}, ${child}, ${THIS}, ${SECTION}, ${kind}, ${status},
           ${status === "new" ? null : "asm"}, ${status === "new" ? null : sql`now()`}
    where not exists (select 1 from sheet_instance where qr_code = ${qr})`;
  await paper(QR.asha, ws[0].id, kids.Asha, "printed", "assessment");
  await paper(QR.bina, ws[1].id, kids.Bina, "printed", "assessment");
  await paper(QR.chetan, ws[2].id, kids.Chetan, "new", "assessment");
  await paper(QR.home, ws[3].id, kids.Dev, "new", "focus");
  await aReadPaper(sql, {
    qr: QR.bina,
    child: kids.Bina,
    template: ws[1].id,
    items: ws[1].item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
    file: "IMG_ASM.pdf",
  });
  // one file whose codes are this assessment's, one whose codes belong to no paper the school printed
  await sql`delete from flow_run where flow = 'read-scan' and (trigger like '%IMG_ASM.pdf' or trigger like '%stranger.pdf')`;
  for (const [file, code] of [["IMG_ASM.pdf", QR.bina], ["stranger.pdf", "CSABCDEF"]] as const) {
    await sql`
      insert into flow_run (tenant_id, flow, trigger, status, finished_at, result)
      values (${tenant}, 'read-scan', ${`upload: ${file}`}, 'ok', now(), ${sql.json({ pages: 1, copies: [{ copy: 1, pages: [1], code, child_id: null, answers: 2 }] })})`;
  }
});
test.afterAll(async () => {
  // leave nothing waiting on Today for the specs that run after this one, and no file in the reading list
  await sql`update sheet_instance set print_status = 'printed', approved_by = coalesce(approved_by, 'asm'), approved_at = coalesce(approved_at, now())
            where section in (${SECTION}, 'ASM-LONG') and print_status = 'new'`;
  await sql`delete from flow_run where flow = 'read-scan' and (trigger like '%IMG_ASM.pdf' or trigger like '%stranger.pdf')`;
  await sql.end();
});

const row = (page: Page, text?: RegExp | string) => {
  const r = page.locator(`tr[data-assessment^='assessment~${SECTION}~${THIS}~']`);
  return text ? r.filter({ hasText: text }) : r;
};

async function gotoClass(page: Page) {
  await page.goto(`/papers?class=${SECTION}`);
  await expect(page.getByRole("heading", { level: 1 }).first()).toHaveText(/Assessments/);
}

test("two equal blocks side by side above the list; no explanatory paragraph in the read block", async ({ page }) => {
  await page.goto("/papers");
  const make = await page.getByRole("region", { name: "Make an assessment" }).boundingBox();
  const readBox = await page.getByRole("region", { name: "Read an assessment" }).boundingBox();
  const table = await page.locator(".data-table").first().boundingBox();
  expect(make && readBox && table).toBeTruthy();
  expect(Math.abs(make!.y - readBox!.y), "same top").toBeLessThan(2);
  expect(readBox!.x, "side by side").toBeGreaterThan(make!.x + make!.width - 2);
  expect(Math.abs(make!.width - readBox!.width), "equal width").toBeLessThan(4);
  expect(table!.y, "the list is below both").toBeGreaterThan(Math.max(make!.y + make!.height, readBox!.y + readBox!.height) - 2);
  // the four ways to make one are in the left block; the right has one drop zone, the Drive link and one button
  for (const w of ["For a class", "For each child", "For one child", "A ready-made worksheet"]) await expect(page.getByRole("region", { name: "Make an assessment" }).getByRole("link", { name: w })).toBeVisible();
  const rb = page.getByRole("region", { name: "Read an assessment" });
  await expect(rb.getByLabel("Choose scans")).toHaveCount(1);
  await expect(rb.getByLabel("Link to the scan on Google Drive")).toBeVisible();
  await expect(rb.getByRole("button", { name: "Read it" })).toBeVisible();
});

test("a tab strip leads to Needs checking and Reading status", async ({ page }) => {
  await page.goto("/papers");
  const tabs = page.getByRole("group", { name: "Assessments tabs" });
  await expect(tabs.getByRole("link")).toHaveText(["Assessments", "Needs checking", "Reading status"]);
  await tabs.getByRole("link", { name: "Needs checking" }).click();
  await expect(page).toHaveURL(/\/capture\/check/);
});

test("an assessment is named from its sheet, never from its file; the file is a small note under it", async ({ page }) => {
  await gotoClass(page);
  const r = row(page);
  await expect(r).toHaveCount(1);
  const name = r.locator("a[aria-expanded]");
  await expect(name).toHaveText(new RegExp(`^${skillName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?: · (?:Easy|Medium|Hard|Advance))? · Grade 2 · class assessment · \\d{2}-[A-Z][a-z]{2}-\\d{4}$`));
  await expect(name).not.toContainText(/\.pdf|IMG_/);
  await expect(r.locator("[data-files]")).toHaveText(/file: IMG_ASM\.pdf/);
});

test("a file that belongs to no assessment says so, in red, with its file name small", async ({ page }) => {
  await page.goto("/papers");
  const g = page.locator("tr[data-unmatched-file='stranger.pdf']");
  await expect(g).toBeVisible();
  await expect(g.locator("[data-unmatched]")).toHaveText("Not matched to an assessment");
  await expect(g.locator("[data-unmatched]")).toHaveClass(/terracotta/);
  await expect(g).toContainText("file: stranger.pdf");
});

test("the steps are in the order the school does them, each an icon, a word and a colour", async ({ page }) => {
  await gotoClass(page);
  const heads = await page.locator(".data-table thead th").allInnerTexts();
  const steps = ["To approve", "Made", "Printed / given", "Uploaded", "Read", "Checked", "Signed off"];
  const at = steps.map((s) => heads.findIndex((h) => h.trim().toLowerCase() === s.toLowerCase()));
  expect(at.every((i) => i >= 0), `all steps in ${heads}`).toBe(true);
  expect([...at].sort((a, b) => a - b), "in order").toEqual(at);
  const r = row(page);
  const chips = r.locator("[data-status]");
  expect(await chips.count()).toBeGreaterThanOrEqual(5);
  for (let i = 0; i < (await chips.count()); i++) {
    await expect(chips.nth(i).locator("svg[data-icon]")).toHaveCount(1);
    expect(["ok", "wait", "act", "quiet"]).toContain(await chips.nth(i).getAttribute("data-tone"));
  }
  // made, and two of the three printed: the second step is partway, the next one still to do
  await expect(r.locator("td").nth(heads.findIndex((h) => /^made$/i.test(h.trim()))).locator("[data-status]")).toHaveAttribute("data-status", "done");
});

test("the row's one action opens the next item", async ({ page }) => {
  await gotoClass(page);
  // an answer waits for a person: that comes before the papers still to print and to come in
  const act = row(page).locator("[data-action]");
  await expect(act).toHaveCount(1);
  await expect(act).toHaveText("Check 1 answer");
  await act.click();
  await expect(page).toHaveURL(/\/capture\/check/);
  await expect(page.getByText("This page could not load")).toHaveCount(0);
});

test("with nothing waiting on a person, the action is what comes next: print, then upload", async ({ page }) => {
  const [t] = await sql<{ tenant_id: string; sheet_template_id: string; child_id: string }[]>`
    select tenant_id, sheet_template_id, child_id from sheet_instance where qr_code = ${QR.asha}`;
  const made = async (qr: string, wk: string, status: string) => sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${t.tenant_id}, ${qr}, ${t.sheet_template_id}, ${t.child_id}, ${wk}, ${SECTION}, 'assessment', ${status},
           ${status === "new" ? null : "asm"}, ${status === "new" ? null : sql`now()`}
    where not exists (select 1 from sheet_instance where qr_code = ${qr})`;
  await made("CSA5A006", "2026-W03", "new");
  await made("CSA5A005", "2026-W02", "printed");
  await sql`update sheet_instance set print_status = 'new', approved_by = null, approved_at = null where qr_code = 'CSA5A006'`;
  await page.goto(`/papers?class=${SECTION}&week=2026-W03`);
  const print = page.locator("[data-action]").first();
  await expect(print).toHaveText("Print");
  await expect(print).toHaveAttribute("href", /\/papers\/card\?/);
  await page.goto(`/papers?class=${SECTION}&week=2026-W02`);
  const upload = page.locator("[data-action]").first();
  await expect(upload).toHaveText("Upload");
  await expect(upload).toHaveAttribute("href", "/papers#read-box");
});

test("a row opens to its children: roll, child, level, the same steps, the score and their pages", async ({ page }) => {
  await gotoClass(page);
  await row(page).locator("a[aria-expanded]").click();
  const kids = page.locator("[data-copies] tr[data-paper]");
  await expect(kids).toHaveCount(3);
  const heads = (await page.locator("[data-copies] thead th").allInnerTexts()).map((h) => h.trim().toLowerCase());
  expect(heads.slice(0, 3)).toEqual(["roll", "child", "level"]);
  for (const s of ["made", "printed / given", "uploaded", "read", "checked", "signed off"]) expect(heads).toContain(s);
  const bina = kids.filter({ hasText: "Bina" });
  await expect(bina.locator("[data-status]").first()).toBeVisible();
  // the child's own pages for this assessment, and from them the whole-page view
  await bina.locator("summary", { hasText: "Open pages" }).click();
  const img = bina.locator("img");
  await expect(img).toHaveCount(1);
  await expect(img.first()).toHaveAttribute("src", /^\/api\/scan\/[0-9a-f-]{36}\/1$/);
  await img.first().locator("xpath=..").click();
  await expect(page).toHaveURL(/\/capture\/[0-9a-f-]{36}$/);
  await expect(page.getByText("This page could not load")).toHaveCount(0);
});

test("an educator renames an assessment; the old name stays as a row, the newest shows", async ({ page }) => {
  // a week of its own, so the names an earlier run kept (evidence is append-only) are not in the way
  const wk = "2026-W02";
  const key = `assessment~${SECTION}~${wk}~`;
  const [t] = await sql<{ tenant_id: string; sheet_template_id: string; child_id: string }[]>`
    select tenant_id, sheet_template_id, child_id from sheet_instance where qr_code = ${QR.asha}`;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at)
    select ${t.tenant_id}, 'CSA5A005', ${t.sheet_template_id}, ${t.child_id}, ${wk}, ${SECTION}, 'assessment', 'printed', 'asm', now()
    where not exists (select 1 from sheet_instance where qr_code = 'CSA5A005')`;
  await page.goto(`/papers?class=${SECTION}&week=${wk}`);
  const r = page.locator(`tr[data-assessment^='${key}']`);
  await expect(r).toHaveCount(1);
  const names = [`Term 2 check ${Date.now()}`, `Term 2 check, retake ${Date.now()}`];
  for (const name of names) {
    await r.locator("summary", { hasText: "Rename" }).click();
    await r.getByLabel("Name this assessment").fill(name);
    await r.getByRole("button", { name: "Save" }).click();
    await expect(r.locator("a[aria-expanded]")).toHaveText(name);
  }
  const rows = await sql<{ name: string }[]>`select name from assessment_name where key like ${key + "%"} order by created_at`;
  expect(rows.map((x) => x.name).slice(-2)).toEqual(names);
});

test("a home assessment starts at To approve with one Approve for its row, never for all", async ({ page }) => {
  await sql`update sheet_instance set print_status = 'new', approved_by = null, approved_at = null where qr_code = ${QR.home}`;
  await page.goto(`/papers?class=${SECTION}&kind=focus`);
  const home = page.locator("tr[data-assessment^='focus~']");
  await expect(home).toHaveCount(1);
  await expect(home.locator("[data-action=approve]")).toHaveText("Approve");
  const heads = (await page.locator(".data-table thead th").allInnerTexts()).map((h) => h.trim().toLowerCase());
  expect(heads.indexOf("to approve")).toBeGreaterThanOrEqual(0);
  expect(heads.indexOf("to approve")).toBeLessThan(heads.indexOf("made"));
  await expect(page.getByText(/approve all/i)).toHaveCount(0);
  await expect(page.getByRole("button", { name: /approve all/i })).toHaveCount(0);
  // a class assessment has no approval step and no Approve
  await page.goto(`/papers?class=${SECTION}&kind=assessment`);
  await expect(page.locator("[data-action=approve]")).toHaveCount(0);
  await page.goto(`/papers?class=${SECTION}&kind=focus`);
  await page.locator("tr[data-assessment^='focus~'] [data-action=approve]").click();
  await expect(page.locator("tr[data-assessment^='focus~'] [data-action]")).toHaveText("Upload");
  const [{ status }] = await sql<{ status: string }[]>`select print_status as status from sheet_instance where qr_code = ${QR.home}`;
  expect(status).toBe("printed");
});

test("Papers to approve is the status filter of this list; the old addresses still work", async ({ page }) => {
  await sql`update sheet_instance set print_status = 'new', approved_by = null, approved_at = null where qr_code = ${QR.home}`;
  await page.goto("/papers/approve");
  await expect(page).toHaveURL(/\/papers\?status=approve/);
  await expect(page.locator("[data-filterbar] select[name=status]")).toHaveValue("approve");
  for (const r of await page.locator("tr[data-assessment]").all()) await expect(r.locator("[data-action]")).toHaveText("Approve");
  for (const path of ["/papers/approve?section=" + SECTION + "&week=" + THIS + "&kind=assessment", "/capture", "/capture/check", "/make", "/worksheets"]) {
    const res = await page.goto(path);
    expect(res?.status(), path).toBeLessThan(400);
    await expect(page.getByText("This page could not load"), path).toHaveCount(0);
  }
});

test("the list is the last ten assessments, newest first, paged", async ({ page }) => {
  const long = "ASM-LONG";
  const kids = await aClass(sql, long, "G2", ["Esha"]);
  const [t] = await sql<{ tenant_id: string; sheet_template_id: string }[]>`select tenant_id, sheet_template_id from sheet_instance where qr_code = ${QR.asha}`;
  for (let i = 0; i < 12; i++) {
    const wk = `2026-W${String(10 + i).padStart(2, "0")}`;
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind, print_status, approved_by, approved_at, created_at)
      select ${t.tenant_id}, ${`CSA5B${String(i).padStart(3, "0")}`}, ${t.sheet_template_id}, ${kids.Esha}, ${wk}, ${long}, 'assessment', 'printed', 'asm', now(),
             now() - ${(12 - i) * 3} * interval '1 day'
      where not exists (select 1 from sheet_instance where qr_code = ${`CSA5B${String(i).padStart(3, "0")}`})`;
  }
  await page.goto(`/papers?class=${long}`);
  const rows = page.locator("tr[data-assessment]");
  await expect(rows).toHaveCount(10);
  // newest first: the week made last is at the top
  await expect(rows.first()).toHaveAttribute("data-assessment", new RegExp("2026-W21~"));
  await expect(page.getByRole("navigation", { name: "Assessments pages" })).toContainText("Page 1 of 2");
  await page.getByRole("link", { name: /Earlier|Later/ }).click();
  await expect(rows).toHaveCount(2);
});
