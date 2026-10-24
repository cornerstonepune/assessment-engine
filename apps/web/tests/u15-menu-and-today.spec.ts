/**
 * U15 — the menu and What needs doing (goals/ui1-menu-and-today.yaml, rewritten for goals/nav_teacher_scope_and_todo.yaml). Nimish, 2026-10-11: "I can't seem to actually find where I
 * go and check the papers or questions for which human validation is required." The menu is the school's order of
 * work, each tab with the count of what waits in it; Today lists every one of those things under the tab where it is
 * done, each line opening that place; nothing hides behind a role; weeks and classes are said in words.
 *
 * The test's own class, its pack for this week and its parent report are made on the copy and cleared afterwards.
 */
import { expect, type Page, test } from "@playwright/test";
import { createHmac } from "node:crypto";
import postgres from "postgres";
import { isoWeek, weekWords } from "../lib/week";
import { ENGINE_PORT } from "../playwright.config";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "UI1-TEST";
const WEEK = isoWeek();
const EDUCATOR = { email: "ui1-educator@cornerstone.test", name: "UI1 educator", role: "educator" };
const GROUPS = ["What needs doing", "Teaching", "Assessments", "Results", "Setup"];

async function engine(path: string, body: object) {
  const r = await fetch(`http://127.0.0.1:${ENGINE_PORT}${path}`, {
    method: "POST",
    headers: {
      "X-Engine-Key": process.env.E2E_ENGINE_KEY!,
      "content-type": "application/json",
      "Idempotency-Key": `ui1-${path}-${Date.now()}`,
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json();
}

/** A Grade 2 child of the test's own, subtraction under half right, with a parent report written and not approved —
 *  the report made again each run, since the clean-up takes it away and the child stays. */
async function testChild(): Promise<string> {
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  let [child] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (!child) {
    [child] = await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G2') returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${child.id}, 'Uione')`;
    for (const right of [false, false, false, false, true, true]) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at, confirmed_by)
        values (${tenant_id}, ${child.id}, 'NUM.OPS.02', 'R6', ${right}, 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${child.id}::uuid)`;
  }
  const body = {
    facts: { grade: "Grade 2", from: "2026-10-01", to: "2026-10-10", answers: 6, can_do: [], nearly: [], improving: [], working_on: [], next: null },
    draft: { summary: "[child] has worked on subtraction this fortnight.", can_do: [], working_on: [], at_home: [] },
  };
  await sql`insert into parent_note (tenant_id, child_id, week, body) values (${tenant_id}, ${child.id}, ${WEEK}, ${JSON.stringify(body)})`;
  return child.id;
}

async function clearUp() {
  await sql`delete from item_exposure where week = ${WEEK} and child_id in (select id from child where section = ${SECTION})`;
  await sql`delete from prescription where child_id in (select id from child where section = ${SECTION})`;
  await sql`delete from sheet_instance where section = ${SECTION}`;
  await sql`delete from parent_note where child_id in (select id from child where section = ${SECTION})`;
  await sql`update config set value = (select coalesce(jsonb_agg(s), '[]') from jsonb_array_elements(value) s where s ->> 'email' <> ${EDUCATOR.email}) where key = 'app.staff'`;
}

/** A signed-in session for someone on the staff list, as the gate checks it (global-setup.ts makes the coordinator's). */
async function signInAs(page: Page, email: string) {
  const expiry = String(Date.now() + 3_600_000);
  const body = `${Buffer.from(email).toString("base64url")}.${expiry}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  await page.context().clearCookies();
  await page.context().addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
}

/** The rows of What needs doing, as {what, where, kind, state}, across every topic's table (the subject sections are open). */
async function rows(page: Page) {
  const out = [];
  for (const tr of await page.locator("tr[data-kind]").all()) {
    out.push({
      kind: (await tr.getAttribute("data-kind"))!,
      state: (await tr.getAttribute("data-state"))!,
      what: (await tr.locator("td[data-label=What]").innerText()).trim(),
      where: (await tr.locator("td[data-label=Where]").innerText()).trim(),
    });
  }
  return out;
}

/** The count the group "What needs doing" carries, 0 when it carries none. */
async function badge(page: Page): Promise<number> {
  const n = page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: /^What needs doing/ }).getByTestId("waiting");
  return (await n.count()) ? Number((await n.innerText()).replace(/\D/g, "")) : 0;
}

test.beforeAll(async () => {
  await clearUp();
  await testChild();
  await engine("/week/prescribe", { section: SECTION, week: WEEK, skill_set: "SUB.2D2D" });
  await engine("/week/assemble", { section: SECTION, week: WEEK });
});
test.afterAll(async () => {
  await clearUp();
  await sql.end();
});

test("the menu is five groups, and only What needs doing carries the count of what waits", async ({ page }) => {
  await page.goto("/today");
  const menu = page.getByRole("navigation", { name: "Sections" });
  const names = await menu.getByRole("link").allInnerTexts();
  expect(names.map((n) => n.replace(/\s*\d[\d,]*$/, "").trim())).toEqual(GROUPS);
  await expect(menu.getByTestId("waiting"), "one count, on one group").toHaveCount(1);
  // the count is what the sections of the page add up to (red and amber; what can wait is said apart)
  const todo = (await page.locator("[data-todo]").evaluateAll((els) => els.map((e) => Number(e.getAttribute("data-todo")))));
  expect(await badge(page), "the group's count is the page's").toBe(todo.reduce((a, b) => a + b, 0));
  for (const [group, heading] of [["Setup", "Curriculum"], ["Assessments", "Assessments"], ["Results", "Class results"], ["Teaching", "Teaching"], ["What needs doing", "What needs doing"]]) {
    await menu.getByRole("link", { name: new RegExp(`^${group}\\b`) }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(menu.getByRole("link", { name: new RegExp(`^${group}\\b`) })).toHaveAttribute("aria-current", "page");
  }
});

test("What needs doing lists everything that waits as rows, and each row's button opens that one item", async ({ page }) => {
  await page.goto("/today?kind=classpaper");
  await expect(page.getByText(/For others|For you/)).toHaveCount(0);

  // the test's own class pack, waiting before it prints: its row opens the page that approves exactly that pack
  const pack = page.locator("tr[data-kind=classpaper]").filter({ hasText: SECTION });
  await expect(pack).toHaveCount(1);
  await expect(pack.locator("[data-status]")).toContainText("this week");
  await pack.getByRole("link").click();
  await expect(page).toHaveURL(new RegExp(`section=${SECTION}&week=${WEEK}&kind=practice`));
  await expect(page.getByRole("button", { name: /Approve/ })).toBeVisible();

  // skills to approve: one row each, as many as the skills the rows say are waiting
  const [{ drafts }] = await sql<{ drafts: number }[]>`select count(*)::int as drafts from skill where status <> 'ratified'`;
  await page.goto("/today?kind=skill");
  const counted = (await page.locator("details[data-topic] > summary .fact").allInnerTexts()).reduce((n, t) => n + Number(t.replace(/\D/g, "")), 0);
  expect(counted, "a row for every skill waiting").toBe(drafts);
  const skill = page.locator("tr[data-kind=skill]").first();
  if (drafts) {
    await skill.getByRole("link").click();
    await expect(page).toHaveURL(/\/skill-sets\/[A-Z0-9_.]+$/);
    await page.goto("/today");
  }

  // a topic not taught is a green row, "when ready": the school's choice, never counted as waiting
  await page.goto("/today?kind=taught");
  const [{ off }] = await sql<{ off: number }[]>`select count(*)::int as off from topic t where not exists (select 1 from child k where k.tenant_id = t.tenant_id and k.active and taught_in(t.tenant_id, t.code, k.section))`;
  const taught = await rows(page);
  expect(taught.every((r) => r.state === "whenReady"), "marking a topic taught is never red or amber").toBe(true);
  expect(taught.length > 0 || off === 0).toBe(true);

  // the test child's parent report, written and not approved: its row opens the reports of that class
  await page.goto("/today?kind=report");
  const report = page.locator("tr[data-kind=report]").filter({ hasText: SECTION });
  await expect(report).toHaveCount(1);
  await expect(report).toContainText("Grade 2");
  await report.getByRole("link").click();
  await expect(page).toHaveURL(new RegExp(`/growth/reports\\?class=${SECTION}`));
  await expect(page.getByText("This page could not load")).toHaveCount(0);
});

test("an educator not mapped to a class sees every row a coordinator sees, and the engineering map", async ({ page }) => {
  // one role for now (goals/ux9c-one-role.yaml): what waits on the coordinator waits on an educator too
  await page.goto("/today");
  const coordinator = await rows(page);
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByRole("dialog", { name: "Menu" }).getByRole("link", { name: "How it works" })).toBeVisible();

  await sql`update config set value = value || ${sql.json([EDUCATOR])} where key = 'app.staff'`;
  await signInAs(page, EDUCATOR.email);
  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What needs doing");
  expect(await rows(page)).toEqual(coordinator);
  await expect(page.getByText(/For others|For you|No one on the staff list/)).toHaveCount(0);
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByRole("dialog", { name: "Menu" }).getByRole("link", { name: "How it works" })).toBeVisible();
});

test("weeks and classes on What needs doing are said in words, not codes", async ({ page }) => {
  await page.goto("/today?kind=classpaper");
  const main = page.getByRole("main");
  await expect(main.getByText(new RegExp(`Grade 2 · ${SECTION} · class practice · ${weekWords(WEEK)}`))).toBeVisible();
  expect(weekWords(WEEK)).toMatch(/^week of \d{1,2} [A-Z][a-z]{2}$/);
  expect(await main.innerText(), "an ISO week code on the page").not.toMatch(/\b\d{4}-W\d{2}\b/);
});
