/**
 * U70 — a coordinator changes a child's grade, or moves them to another class (goals/mov_move_a_child.yaml).
 *
 * Nimish, 27 Oct 2026: a child to be moved to Grade 4, and the data "in a structured way. It's not like some hard-coded
 * backend". The whole flow on a child's page: pick, read the sentence, confirm; a taken roll; a teacher with no buttons
 * and a form posted by hand; the history. Children and classes are the test's own, named afresh each run, and no real
 * child is in any of it (rule 6).
 */
import { expect, test, type Browser } from "@playwright/test";
import { createHmac } from "node:crypto";
import postgres from "postgres";
import { aClass } from "./rows";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const RUN = Date.now().toString(36).toUpperCase();
const FROM = `MVA-${RUN}`; // Grade 3, six children
const TO = `MVB-${RUN}`; // Grade 4, two children: rolls 1 and 2
const kids: Record<string, string> = {};
let tenant: string;

test.beforeAll(async () => {
  [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  Object.assign(kids, await aClass(sql, FROM, "G3", ["Ann", "Bea", "Cai", "Dev", "Eli", "Fay"]));
  Object.assign(kids, await aClass(sql, TO, "G4", ["Gus", "Hal"]));
});
test.afterAll(async () => {
  await sql.end();
});

const row = async (id: string) => (await sql<{ band: string; section: string; roll_no: string }[]>`select band, section, roll_no from child where id = ${id}`)[0];
const moves = (id: string) => sql<{ to_band: string; reason: string }[]>`select to_band, reason from child_move where child_id = ${id}`;

test("the grades offered are the rows of the grade table, in its order", async ({ page }) => {
  await page.goto(`/growth/${kids.Ann}`);
  const offered = await page.locator('[data-testid="change-grade"] select option').evaluateAll((o) => o.map((x) => (x as HTMLOptionElement).value));
  const table = await sql<{ code: string }[]>`select g.code from grade g join tenant t on t.id = g.tenant_id order by g.ord`;
  expect(offered).toEqual(table.map((g) => g.code));
});

test("a coordinator changes a grade after a confirm screen, and the history shows it", async ({ page }) => {
  await page.goto(`/growth/${kids.Ann}`);
  await expect(page.getByTestId("where")).toContainText(`${FROM}`);
  await page.locator('[data-testid="change-grade"] select').selectOption("G4");
  await page.getByRole("button", { name: "Review the change" }).click();
  const sentence = page.getByTestId("move-sentence");
  await expect(sentence).toContainText("Change Ann's grade from");
  await expect(sentence).toContainText(`They stay in ${FROM}, roll 1.`);
  await expect(sentence).toContainText("Their answers and results stay with them. Papers already printed stay as they are.");
  expect((await row(kids.Ann)).band, "nothing is written before Confirm").toBe("G3");
  await page.getByLabel("Reason (optional)").fill("ready for the next grade");
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("status").first()).toContainText("Done.");
  expect(await row(kids.Ann)).toEqual({ band: "G4", section: FROM, roll_no: "1" });
  const history = page.getByTestId("move-history");
  await expect(history.locator("li")).toHaveCount(1);
  await expect(history).toContainText("ready for the next grade");
  await expect(history).toContainText("End-to-end test");
  expect(await moves(kids.Ann)).toEqual([{ to_band: "G4", reason: "ready for the next grade" }]);
});

test("Cancel writes nothing", async ({ page }) => {
  await page.goto(`/growth/${kids.Bea}`);
  await page.locator('[data-testid="change-grade"] select').selectOption("G4");
  await page.getByRole("button", { name: "Review the change" }).click();
  await page.getByRole("link", { name: "Cancel" }).click();
  await expect(page.getByTestId("confirm-move")).toHaveCount(0);
  expect((await row(kids.Bea)).band).toBe("G3");
  expect(await moves(kids.Bea)).toEqual([]);
});

test("a move to a class that works at another grade asks which grade, keeps the same child, and shows in the history", async ({ page }) => {
  // something that is the child's own, to see it stay with them
  const [tpl] = await sql<{ id: string }[]>`
    insert into sheet_template (tenant_id, band, child_id, week, key, batch_id) values (${tenant}, 'G3', ${kids.Cai}, ${"MV-" + RUN}, ${sql.json({ code: "MV" })}, ${"MV" + RUN}) returning id`;
  await sql`insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status) values (${tenant}, ${"CS" + RUN.padEnd(6, "0").slice(-6)}, ${tpl.id}, ${kids.Cai}, 'new')`;

  await page.goto(`/growth/${kids.Cai}`);
  await page.locator('[data-testid="move-class"] select').selectOption(TO);
  await page.locator('[data-testid="move-class"] input[name="roll"]').fill("12");
  await page.getByRole("button", { name: "Review the move" }).click();
  await expect(page.getByTestId("ask-grade")).toContainText(`${TO} works at`);
  await page.getByRole("button", { name: "Review the move" }).click(); // the class's grade, as offered
  await expect(page.getByTestId("move-sentence")).toContainText(`Move Cai from ${FROM} roll 3 to ${TO} roll 12.`);
  await expect(page.getByTestId("move-sentence")).toContainText("Their answers and results stay with them. Papers already printed stay as they are.");
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("status").first()).toContainText("Done.");
  expect(await row(kids.Cai)).toEqual({ band: "G4", section: TO, roll_no: "12" });
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from sheet_instance where child_id = ${kids.Cai}`;
  expect(n, "the same child, so their paper is still theirs").toBe(1);
  await expect(page.getByTestId("move-history")).toContainText(`${FROM} roll 3 → ${TO} roll 12`);
  // the class page now lists them in the new class
  await page.goto(`/growth/class/${TO}`);
  await expect(page.locator("main")).toContainText("3 children");
});

test("a roll number that is taken is said in words and nothing changes", async ({ page }) => {
  await page.goto(`/growth/${kids.Dev}`);
  await page.locator('[data-testid="move-class"] select').selectOption(TO);
  await page.locator('[data-testid="move-class"] input[name="roll"]').fill("2");
  await page.getByRole("button", { name: "Review the move" }).click();
  await expect(page.getByRole("status").first()).toContainText(`Roll 2 in ${TO} is taken by another child. Nothing was changed.`);
  await expect(page.getByRole("button", { name: "Confirm" })).toHaveCount(0);
  expect(await row(kids.Dev)).toEqual({ band: "G3", section: FROM, roll_no: "4" });
  expect(await moves(kids.Dev)).toEqual([]);
});

const TEACHER = { email: `mv-teacher-${RUN.toLowerCase()}@cornerstone.test`, name: "Mv Teacher", role: "educator", classes: [FROM], subjects: ["NUM"] };
async function asTeacher(browser: Browser) {
  await sql`update config set value = value || ${sql.json([TEACHER])} where key = 'app.staff' and not value @> ${sql.json([{ email: TEACHER.email }])}`;
  const body = `${Buffer.from(TEACHER.email).toString("base64url")}.${Date.now() + 3_600_000}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  const context = await browser.newContext({ baseURL: "http://localhost:3100", viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
  return { context, page: await context.newPage() };
}

test("a teacher sees the section and its history but no buttons, and a form posted by hand changes nothing", async ({ browser, page }) => {
  // the coordinator's confirm form, read as the browser holds it
  await page.goto(`/growth/${kids.Eli}?act=grade&band=G4`);
  const fields = await page.locator('[data-testid="confirm-move"] input').evaluateAll((els) => els.map((e) => [(e as HTMLInputElement).name, (e as HTMLInputElement).value]));
  expect(fields.length).toBeGreaterThan(3);

  const { context, page: teacher } = await asTeacher(browser);
  await teacher.goto(`/growth/${kids.Eli}`);
  await expect(teacher.locator("#grade-class")).toContainText("Only the coordinator changes a child's grade or class.");
  await expect(teacher.locator("#grade-class")).toContainText(`${FROM}`);
  await expect(teacher.locator("#grade-class").getByRole("button")).toHaveCount(0);
  await expect(teacher.getByTestId("change-grade")).toHaveCount(0);
  // even with the address of a review, no confirm form is drawn for a teacher
  await teacher.goto(`/growth/${kids.Eli}?act=grade&band=G4`);
  await expect(teacher.getByTestId("confirm-move")).toHaveCount(0);

  // the same post, made by hand: a coordinator's changes the grade (so the post is well formed), a teacher's does not
  const post = { headers: { origin: "http://localhost:3100" }, multipart: Object.fromEntries(fields) };
  await teacher.request.post(`/growth/${kids.Eli}?act=grade&band=G4`, post);
  expect((await row(kids.Eli)).band, "the server refused the teacher").toBe("G3");
  expect(await moves(kids.Eli)).toEqual([]);
  await page.request.post(`/growth/${kids.Eli}?act=grade&band=G4`, post);
  expect((await row(kids.Eli)).band, "the coordinator's identical post is accepted").toBe("G4");
  await context.close();
});
