/**
 * S42 — one assessment as one card, Made to Results (goals/s2-the-assessment-card.yaml). Slice S2 of the scope Nimish
 * locked on 2026-10-22: "the assessment as one card moving Made → approved for print → Given → Papers in → Read →
 * Checked → Signed off → Results".
 *
 * A Grade 2 class of the test's own (made once and kept: evidence is append-only), and each run its own assessments,
 * their printed codes new each run, so the card starts at Made every time: a class practice paper for Asha, Bina and
 * Chetan, with a spare; and a class assessment that comes back with no one saying it was given.
 */
import { randomBytes } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "S42-CLASS";
const RUN = randomBytes(2).toString("hex").toUpperCase();
const code = (n: string) => `CS${RUN}${n}`; // CS + 4 hex of the run + 2 hex of the copy
const QR = { Asha: code("A1"), Bina: code("A2"), Chetan: code("A3"), spare: code("AF") };
let kids: Record<string, string> = {};
let ws: { id: string; item_ids: string[]; set: string; title: string };
let week = "";
let tenant = "";

const card = (kind: string) => `/papers/card?${new URLSearchParams({ class: SECTION, week, kind, set: ws.set })}`;
const at = (page: Page) => page.getByRole("list", { name: "Where it stands" }).locator("[aria-current=step]");

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan"]);
  [{ tenant, week }] = await sql<{ tenant: string; week: string }[]>`
    select tenant_id as tenant, to_char(now(), 'IYYY-"W"IW') as week from child where id = ${kids.Asha}`;
  [ws] = await sql<{ id: string; item_ids: string[]; set: string; title: string }[]>`
    select t.id, t.item_ids, t.skill_set_code as set, s.name || ' · ' || t.difficulty as title
    from sheet_template t join skill_set s on s.code = t.skill_set_code
    where t.source = 'library' and t.retired_at is null and t.band = 'G2' and cardinality(t.item_ids) >= 2 order by t.code limit 1`;
  // an earlier run's papers are put away, as a paper made in error is: the card holds this run's alone
  await sql`update sheet_instance set print_status = 'void' where section = ${SECTION} and qr_code not like ${`CS${RUN}%`}`;
  for (const [who, qr] of Object.entries(QR)) {
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, section, week, kind, print_status)
      values (${tenant}, ${qr}, ${ws.id}, ${who === "spare" ? null : kids[who]}, ${SECTION}, ${week}, 'practice', 'new')`;
  }
  // the class assessment, printed, whose papers come back with no one pressing "Given on"
  for (const [who, n] of [["Asha", "B1"], ["Bina", "B2"]] as const) {
    await sql`
      insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, section, week, kind, print_status,
                                  approved_by, approved_at, printed_at)
      values (${tenant}, ${code(n)}, ${ws.id}, ${kids[who]}, ${SECTION}, ${week}, 'assessment', 'printed', 'e2e', now(), now())`;
  }
});
test.afterAll(async () => {
  await sql`delete from flow_run where flow = 'read-scan' and trigger like 's42:%'`;
  await sql.end();
});

test("at Made the card shows each child's proposed paper and opens the place to change it", async ({ page }) => {
  await page.goto(card("practice"));
  await expect(at(page)).toContainText("Approved for print");
  const papers = page.getByRole("table", { name: "Each child's paper" });
  for (const who of ["Asha", "Bina", "Chetan"]) {
    await expect(papers.getByRole("row").filter({ hasText: who })).toContainText(ws.title);
  }
  await page.getByRole("link", { name: "Look over and approve for print →" }).click();
  await expect(page).toHaveURL(new RegExp(`/papers/approve\\?section=${SECTION}&week=${week}&kind=practice`));
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Class papers to approve");
});

test("the upload box is at the top of the card, Assessments and Marking", async ({ page }) => {
  for (const path of [card("practice"), "/papers", "/capture"]) {
    await page.goto(path);
    // the page itself, past its loading screen, and the upload box drawn on it
    const box = page.getByText("Choose scans or drop them here").first();
    await expect(box, path).toBeVisible();
    const upload = (await box.boundingBox())!;
    const h1 = (await page.getByRole("heading", { level: 1 }).boundingBox())!;
    expect(upload.y, path).toBeGreaterThan(h1.y);
    // above everything else the page holds: the first panel under the heading
    const firstPanel = await page.locator("main .panel").first().evaluate((el) => !!el.querySelector('input[type=file]'));
    expect(firstPanel, `${path}: the upload is the first panel`).toBe(true);
  }
});

test("the card moves from Made to Results, always showing its next step", async ({ page }) => {
  // approved for print, as the approve page does
  await sql`update sheet_instance set print_status = 'printed', approved_by = 'e2e', approved_at = now(), printed_at = now()
            where qr_code in ${sql(Object.values(QR))}`;
  await page.goto(card("practice"));
  await expect(at(page)).toContainText("Given");
  await page.getByLabel("Day it was given").fill(new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }));
  await page.getByRole("button", { name: "Given on" }).click();
  await expect(page.getByTestId("given")).toContainText("Given on");
  await expect(at(page)).toContainText("Papers in");
  await expect(page.getByTestId("in")).toHaveText(/0 of 3 in · missing: roll 1, roll 2, roll 3/);

  const asha = await aReadPaper(sql, { qr: QR.Asha, child: kids.Asha, template: ws.id, items: ws.item_ids.slice(0, 2), reads: [{ status: "correct", read: "1" }, { status: "correct", read: "2" }] });
  const bina = await aReadPaper(sql, { qr: QR.Bina, child: kids.Bina, template: ws.id, items: ws.item_ids.slice(0, 2), reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }] });
  await page.reload();
  await expect(page.getByTestId("in")).toHaveText(/2 of 3 in · missing: roll 3/);
  // Chetan was away: his paper is held for later, not missing
  await page.getByRole("row").filter({ hasText: "Chetan" }).getByRole("button", { name: "Away: hold it for later" }).click();
  await expect(page.getByTestId("in")).toHaveText(/2 of 3 in · away, held for later: roll 3/);
  await expect(at(page)).toContainText("Checked");
  await expect(page.getByRole("link", { name: "Check them →" })).toBeVisible();

  // a person settles Bina's answer, which signs her paper off; Asha's waits to be signed off
  await sql`select resolve_result(${bina.results[1]}::uuid, 'correct', '{}', 'e2e')`;
  await page.reload();
  await expect(at(page)).toContainText("Signed off");
  await expect(page.getByRole("link", { name: "Sign them off →" })).toBeVisible();
  await sql`select confirm_results(${kids.Asha}::uuid, 'e2e', ${asha.capture}::uuid)`;
  await page.reload();
  await expect(at(page)).toContainText("Results");
  const asha_row = page.getByRole("row").filter({ hasText: "Asha" });
  await expect(asha_row).toContainText("2 of 2");
  await asha_row.getByRole("link", { name: "Asha" }).click();
  await expect(page).toHaveURL(new RegExp(`/growth/${kids.Asha}$`));
});

test("a page to photograph again is flagged, a child away is carried, the papers not back are listed", async ({ page }) => {
  // the newest file holding Chetan's copy lacked its second page, as the engine words it
  await sql`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, result)
    values (${tenant}, 'read-scan', 's42: class scan.pdf', 'ok', now(),
            ${sql.json({ copies: [{ copy: 3, pages: [5], code: QR.Chetan, child_id: kids.Chetan, answers: 1, lacks: ["page 2 is not in the file"] }] })})`;
  // printed, and Chetan not said to be away, whichever test ran before: the newest word stands
  await sql`update sheet_instance set print_status = 'printed', approved_by = 'e2e', approved_at = now(), printed_at = now()
            where qr_code in ${sql(Object.values(QR))} and print_status = 'new'`;
  await sql`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, request)
    values (${tenant}, 'absent', 'e2e: back', 'ok', now(), ${sql.json({ qr: QR.Chetan, away: false, by: "e2e" })})`;
  await page.goto(card("practice"));
  const flag = page.getByRole("alert", { name: "To photograph again" });
  await expect(flag).toContainText("Roll 3: page 2 is not in the file");
  // a paper not back is listed by roll; away, it is carried; back, it is missing again
  await expect(page.getByTestId("in")).toHaveText(/missing: [^·]*roll 3/);
  const chetan = page.getByRole("row").filter({ hasText: "Chetan" });
  await chetan.getByRole("button", { name: "Away: hold it for later" }).click();
  await expect(page.getByTestId("in")).toHaveText(/away, held for later: roll 3/);
  await chetan.getByRole("button", { name: "Back: count as missing" }).click();
  await expect(page.getByTestId("in")).toHaveText(/missing: [^·]*roll 3/);
});

test("papers put in without Given on are read, and the card says it was given", async ({ page }) => {
  await aReadPaper(sql, { qr: code("B1"), child: kids.Asha, template: ws.id, items: ws.item_ids.slice(0, 2), reads: [{ status: "correct", read: "1" }, { status: "correct", read: "2" }] });
  await page.goto(card("assessment"));
  await expect(page.getByTestId("given")).toHaveText("Papers are in, so it was given; no one said the day.");
  await expect(page.getByTestId("in")).toHaveText(/1 of 2 in · missing: roll 2/);
  await expect(at(page)).toContainText("Papers in");
});

test("while a file is read the card says page n of N and about how long", async ({ page }) => {
  await sql`
    insert into flow_run (tenant_id, flow, trigger, status, started_at, result)
    values (${tenant}, 'read-scan', 's42: reading.pdf', 'running', now() - interval '2 minutes',
            jsonb_build_object('pages', 20, 'read', jsonb_build_object('pages', 7, 'of', 20, 'at', now())))`;
  try {
    await page.goto(card("assessment"));
    await expect(page.getByTestId("reading")).toHaveText(/Reading a file now: page 7 of 20, about 4 minutes left\./);
  } finally {
    await sql`update flow_run set status = 'ok', finished_at = now() where flow = 'read-scan' and trigger = 's42: reading.pdf'`;
  }
});
