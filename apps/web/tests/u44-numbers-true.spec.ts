/**
 * U44 — Every number true, and the educator's own (goals/ux8a-numbers-true.yaml). Nimish, 2026-10-21: "focus on the
 * UI/UX first, on whatever we have right now for math, making sure that every screen and every other representation is
 * thought through well: it's clear, it's accurate, clickability is fine."
 *
 * Two Grade 2 classes of the test's own, made once and kept (evidence is append-only). In U44-MINE, Asha's paper on
 * 2-digit + 2-digit at Medium (a Grade 2 level) is read and signed off, and a second paper of hers has one answer the
 * reader could not settle; Bina has a home assessment this week. In U44-OTHER, Chetan has two answers waiting. The
 * educator teaches U44-MINE only. What each page says is checked against those rows, never against the page's own query.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { isoWeek } from "../lib/week";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U44-MINE";
const OTHER = "U44-OTHER";
const THIS = isoWeek();
const QR = { signed: "CS44A001", waiting: "CS44A002", other: "CS44C001", home: "CS44B0F1" };
const EDUCATOR = { email: "u44-educator@cornerstone.test", name: "U44 Educator", role: "educator", classes: [MINE] };
const PASSWORD = "u44-a-long-test-password";
const SALT = "44112233445566778899aabbccddeeff";

test.beforeAll(async () => {
  const mine = await aClass(sql, MINE, "G2", ["Asha", "Bina"]);
  const other = await aClass(sql, OTHER, "G2", ["Chetan"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${mine.Asha}`;
  // two library worksheets of 2-digit + 2-digit at Medium, whose level the school files under Grade 2
  const ws = await sql<{ id: string; item_ids: string[] }[]>`
    select st.id, st.item_ids from sheet_template st join skill_level l on l.skill_code = st.skill_set_code and l.difficulty = st.difficulty
    where st.source = 'library' and st.retired_at is null and st.skill_set_code = 'ADD.2D2D' and st.difficulty = 'Medium'
      and l.grade = 'G2' order by st.code limit 2`;
  const [had] = await sql`select 1 from sheet_instance where qr_code = ${QR.signed}`;
  if (!had) {
    const read = await aReadPaper(sql, {
      qr: QR.signed,
      child: mine.Asha,
      template: ws[0].id,
      items: ws[0].item_ids.slice(0, 3),
      reads: [{ status: "correct", read: "1" }, { status: "correct", read: "1" }, { status: "correct", read: "1" }],
    });
    await sql`select confirm_results(${mine.Asha}::uuid, 'e2e', ${read.capture}::uuid)`;
    await aReadPaper(sql, { qr: QR.waiting, child: mine.Asha, template: ws[1].id, items: ws[1].item_ids.slice(0, 1), reads: [{ status: "needs_teacher", read: "7" }] });
    await aReadPaper(sql, {
      qr: QR.other,
      child: other.Chetan,
      template: ws[1].id,
      items: ws[1].item_ids.slice(0, 2),
      reads: [{ status: "needs_teacher", read: "7" }, { status: "needs_teacher", read: "8" }],
    });
  }
  await sql`delete from sheet_instance where qr_code = ${QR.home}`;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, kind, print_status)
    values (${tenant}, ${QR.home}, ${ws[0].id}, ${mine.Bina}, ${THIS}, 'focus', 'new')`;
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([{ ...EDUCATOR, password }])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`delete from sheet_instance where qr_code = ${QR.home}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const page = await (await browser.newContext({ storageState: { cookies: [], origins: [] } })).newPage();
  await page.goto("/login");
  await page.getByLabel("School email").fill(EDUCATOR.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

const num = (s: string | null) => Number((s ?? "").replace(/[^\d]/g, "") || 0);

test("Today's queue counts the educator's own classes, as the line above it does", async ({ browser }) => {
  const page = await asEducator(browser);
  const toCheck = num(await page.getByRole("region", { name: "Answers to check" }).getByTestId("count").textContent());
  // the educator's one waiting answer is Asha's; Chetan's two are another class's
  expect(toCheck).toBe(1);
  const table = page.getByRole("table", { name: "Answers read, week by week" });
  const waiting = await table.locator("tbody tr td:nth-child(5)").allTextContents();
  expect(waiting.reduce((n, s) => n + num(s), 0), "Still waiting, summed over the weeks shown").toBe(toCheck);
  await page.context().close();
});

test("Marking says the reader's record is every class's, where it sits beside the educator's own counts", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/capture");
  await expect(page.getByRole("region", { name: "How the reader is doing" })).toContainText(/every class/i);
  await page.context().close();
});

test("a paper that came back and was read says so, never that it waits for approval", async ({ page }) => {
  await page.goto(`/worksheets/${QR.signed}`);
  const main = page.locator("main");
  await expect(main).toContainText(/came back/i);
  await expect(main).not.toContainText(/approve the pack/i);
  await expect(main).not.toContainText(/teacher/i);
});

test("a paper's line says who it is for in words: never null, a home assessment by its name", async ({ page }) => {
  await page.goto(`/worksheets/${QR.signed}`);
  await expect(page.locator("main")).not.toContainText(/\bnull\b|\bundefined\b/);
  await page.goto(`/worksheets/${QR.home}`);
  await expect(page.locator("main")).toContainText(/home assessment/i);
  await expect(page.locator("main")).not.toContainText(/\bfocus\b/);
});

test("Curriculum counts a child under the grade of the level they answered", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto("/");
  const curriculum = page.getByRole("table", { name: "The curriculum, grade by grade" });
  // Asha answered at Medium, Grade 2's level; 2-digit + 2-digit's Easy is Grade 1's, which no child of the class answered
  const children = (grade: string) => curriculum.locator(`tr[data-row="${grade}"] td`).nth(-2);
  await expect(children("G2")).toHaveText("1");
  await expect(children("G1")).toHaveText("—");
  await page.context().close();
});

test("a link to a class's week that is not on the list says so, and shows nothing of another class", async ({ browser }) => {
  const page = await asEducator(browser);
  await page.goto(`/papers/approve?section=${OTHER}&week=${THIS}&kind=practice`);
  const main = page.locator("main");
  await expect(main).toContainText(new RegExp(`${OTHER}.*(no papers|not one of your classes)`, "i"));
  await page.context().close();
});
