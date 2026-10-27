/**
 * Who sees a child's answers and papers (goals/own_who_sees_answers.yaml). Nimish, 27 Oct 2026: "The skill and the curriculum
 * is something at a subject level that is open to all teachers ... but their assessments, answers to be checked etc. should be
 * restricted to their grade. Right now 147 answers to check comes to everyone. But Achal should only see the papers he has
 * uploaded." The rule is `staff_sees` (migration 20261222090000); this walks it as two educators and the coordinator.
 *
 * Two classes of the test's own. Achal teaches U67-A and put in two papers: one of his class, one of U67-N's. Neha teaches
 * U67-N; a third paper of her class was put in by nobody known. Each paper has one answer waiting for a person.
 */
import { createHmac } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const A = "U67-A";
const N = "U67-N";
const FILE = "u67-achal-upload.pdf";
const ACHAL = { email: "u67-achal@cornerstone.test", name: "U67 Achal", role: "educator", classes: [A] };
const NEHA = { email: "u67-neha@cornerstone.test", name: "U67 Neha", role: "educator", classes: [N] };
const NOT_YOURS = "This paper belongs to another class";
type Paper = { sheet: string; capture: string; results: string[]; child: string };
let mine: Paper; // Achal's class, put in by Achal
let crossed: Paper; // Neha's class, put in by Achal
let hers: Paper; // Neha's class, put in by nobody known
let run: string;

const offList = (emails: string[]) => sql`
  update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                             where not (s ->> 'email' = any(${emails})))
  where key = 'app.staff'`;

test.beforeAll(async () => {
  const a = await aClass(sql, A, "G2", ["Asha"]);
  const n = await aClass(sql, N, "G2", ["Neel", "Nita"]);
  await offList([ACHAL.email, NEHA.email]);
  await sql`update config set value = value || ${sql.json([ACHAL, NEHA])} where key = 'app.staff'`;
  const [{ achal }] = await sql<{ achal: string }[]>`select staff_id(${ACHAL.email}) as achal`;
  const [ws] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template
    where source = 'library' and retired_at is null and skill_set_code = 'ADD.2D2D' and difficulty = 'Medium' order by code limit 1`;
  const paper = async (qr: string, child: string, by: string | null): Promise<Paper> => {
    const p = await aReadPaper(sql, {
      qr,
      child,
      template: ws.id,
      items: ws.item_ids.slice(0, 2),
      reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
    });
    await sql`update capture set uploaded_by = ${by}::uuid where id = ${p.capture}`;
    return { ...p, child };
  };
  mine = await paper("CSU67A01", a.Asha, achal);
  crossed = await paper("CSU67X01", n.Neel, achal);
  hers = await paper("CSU67N01", n.Nita, null);
  // the file Achal put in, as the engine keeps its run (`inbox.read`): the two copies read from it
  await sql`delete from flow_run where flow = 'read-scan' and result ->> 'file' = ${FILE}`;
  [{ id: run }] = await sql<{ id: string }[]>`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, uploaded_by, result)
    select id, 'read-scan', ${`upload: ${FILE}`}, 'ok', now(), ${achal}::uuid,
           ${sql.json({ file: FILE, pages: 2, copies: [
             { copy: 1, pages: [1], code: "CSU67A01", child_id: a.Asha, answers: 2, capture_id: mine.capture },
             { copy: 2, pages: [2], code: "CSU67X01", child_id: n.Neel, answers: 2, capture_id: crossed.capture },
           ] })}
    from tenant limit 1 returning id`;
});
test.afterAll(async () => {
  await sql`delete from flow_run where id = ${run}::uuid`;
  await offList([ACHAL.email, NEHA.email]);
  await sql.end();
});

/** A member of staff signed in, as the site signs one in. */
async function as(browser: Browser, email: string): Promise<Page> {
  const body = `${Buffer.from(email).toString("base64url")}.${Date.now() + 3_600_000}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  const context = await browser.newContext({ baseURL: "http://localhost:3100", viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
  return context.newPage();
}

async function open(page: Page, url: string) {
  await page.goto(url);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
}

const number = (t: string | null) => Number((t ?? "").replace(/\D/g, "") || 0);

/** The figures a person is shown, each beside the list it counts. */
async function figures(page: Page) {
  await open(page, "/today");
  const menu = page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: /^What needs doing/ }).getByTestId("waiting");
  const badge = (await menu.count()) ? number(await menu.innerText()) : 0;
  const todo = (await page.locator("[data-todo]").evaluateAll((els) => els.map((e) => Number(e.getAttribute("data-todo"))))).reduce((x, y) => x + y, 0);
  await open(page, "/papers");
  const assessments = number(await page.getByRole("link", { name: /answers to check/ }).first().innerText());
  await open(page, "/capture/check");
  const counted = page.locator('[data-count="answers to check"]');
  const check = (await counted.count()) ? number(await counted.first().innerText()) : 0;
  const listed = (await page.locator('tr[data-assessment] > td[data-label="Answers left"]').allInnerTexts()).reduce((x, t) => x + number(t), 0);
  const classes = await page.locator("tr[data-assessment]").evaluateAll((els) => els.map((e) => e.getAttribute("data-assessment")!.split("~")[1]));
  return { badge, todo, assessments, check, listed, classes };
}

test("curriculum, skills and the question bank stay open to an educator of another class", async ({ browser }) => {
  const neha = await as(browser, NEHA.email);
  for (const url of ["/", "/skill-sets/ADD.2D2D", "/library", "/skill-sets/approve"]) {
    await open(neha, url);
    await expect(neha.getByText(/not one of your classes|belongs to another class/i), url).toHaveCount(0);
  }
  await neha.context().close();
});

test("an educator of another class sees none of the paper, and its link and its sign-off are refused in words", async ({ browser }) => {
  const neha = await as(browser, NEHA.email);
  // the lists: Check answers, Assessments, Upload papers, the search
  await open(neha, "/capture/check");
  const classes = await neha.locator("tr[data-assessment]").evaluateAll((els) => els.map((e) => e.getAttribute("data-assessment")!.split("~")[1]));
  expect(classes, "only her class's papers wait for her").toEqual([N]);
  await open(neha, "/papers");
  await expect(neha.locator("main")).not.toContainText(A);
  // the file Achal put in holds a paper of her class: she sees the file, counted by her copy alone
  await open(neha, "/capture");
  const line = neha.locator("tr", { hasText: FILE });
  await expect(line.locator('td[data-label="Copies read"]')).toHaveText("1");
  await expect(line.locator('td[data-label="Answers"]')).toHaveText("2");
  // the links: the paper, one of its answers, its scan, its child
  await open(neha, `/capture/${mine.sheet}`);
  await expect(neha.getByText(NOT_YOURS)).toBeVisible();
  await open(neha, `/capture/check?id=${mine.results[1]}`);
  await expect(neha.getByText(NOT_YOURS)).toBeVisible();
  expect((await neha.request.get(`/api/scan/${mine.capture}/1`)).status(), "its scan").toBe(403);
  await open(neha, `/growth/${mine.child}`);
  await expect(neha.getByText("This child's class is not one of your classes")).toBeVisible();
  // the sign-off: her own paper's form, sent with Achal's paper in it, is refused in words and changes nothing
  await open(neha, `/capture/${hers.sheet}`);
  const form = neha.locator("form:has(input[name=paper_id])").filter({ has: neha.locator("input[name=child_id]") }).first();
  await form.evaluate((f, p) => {
    (f.querySelector("input[name=paper_id]") as HTMLInputElement).value = p.sheet;
    (f.querySelector("input[name=child_id]") as HTMLInputElement).value = p.child;
  }, mine);
  await form.locator("button[type=submit]").click();
  await expect(neha.getByText(NOT_YOURS)).toBeVisible();
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from item_result where capture_id = ${mine.capture} and state = 'confirmed'`;
  expect(n, "nothing of Achal's paper was signed").toBe(0);
  await neha.context().close();
});

test("for each person the counts in the menu, What needs doing and Assessments agree with the lists behind them", async ({ browser, page }) => {
  for (const [who, p, waiting] of [
    ["Achal", await as(browser, ACHAL.email), 2],
    ["Neha", await as(browser, NEHA.email), 2],
    ["the coordinator", page, null],
  ] as const) {
    const f = await figures(p);
    expect(f.badge, `${who}: the menu's figure is What needs doing's`).toBe(f.todo);
    expect(f.assessments, `${who}: Assessments says what Check answers says`).toBe(f.check);
    if (waiting !== null) {
      // an educator's list is one page: every answer the figure counts is a line of it, and no more
      expect(f.check, `${who}: their own answers, not everyone's`).toBe(waiting);
      expect(f.listed, `${who}: the list behind the figure`).toBe(f.check);
    } else {
      expect(f.check, "the coordinator's figure counts every class's").toBeGreaterThanOrEqual(3);
    }
  }
});

test("the educator who uploaded a paper of another class sees it, and the coordinator sees both", async ({ browser, page }) => {
  const achal = await as(browser, ACHAL.email);
  await open(achal, "/capture/check");
  const classes = await achal.locator("tr[data-assessment]").evaluateAll((els) => els.map((e) => e.getAttribute("data-assessment")!.split("~")[1]));
  expect(classes.sort(), "his class, and the paper of another class he put in").toEqual([A, N]);
  await open(achal, `/capture/${crossed.sheet}`);
  await expect(achal.getByText(NOT_YOURS)).toHaveCount(0);
  await open(achal, `/capture/${hers.sheet}`);
  await expect(achal.getByText(NOT_YOURS), "a paper of that class he did not put in").toBeVisible();
  await open(achal, "/capture");
  await expect(achal.locator("tr", { hasText: FILE }).locator('td[data-label="Copies read"]'), "his file, both its copies").toHaveText("2");
  await achal.context().close();
  for (const p of [mine, crossed, hers]) {
    await open(page, `/capture/${p.sheet}`);
    await expect(page.getByText(NOT_YOURS)).toHaveCount(0);
  }
  for (const section of [A, N]) {
    await open(page, `/papers?class=${section}`);
    await expect(page.locator("main")).toContainText(section);
  }
});
