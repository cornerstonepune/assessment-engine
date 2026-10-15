/**
 * U15 — the menu and Today (goals/ui1-menu-and-today.yaml). Nimish, 2026-10-11: "I can't seem to actually find where I
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
const TABS = ["Today", "Curriculum", "Assessments", "Children"];

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

/** {line title: its count} for every line under one tab's heading on Today, and whether it adds to the tab's count. */
async function lines(page: Page, tab: string): Promise<{ title: string; n: number; waits: boolean }[]> {
  const group = page.getByRole("region", { name: tab, exact: true });
  await expect(group).toBeVisible();
  const out = [];
  for (const line of await group.getByTestId("line").all()) {
    out.push({
      title: (await line.getByRole("heading").innerText()).trim(),
      n: Number((await line.getByTestId("count").innerText()).replace(/\D/g, "")),
      waits: (await line.getAttribute("data-waits")) === "yes",
    });
  }
  return out;
}

/** The count a menu tab carries, 0 when it carries none. */
async function badge(page: Page, tab: string): Promise<number> {
  const link = page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: new RegExp(`^${tab}\\b`) });
  const n = link.getByTestId("waiting");
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

test("the menu is Today, Curriculum, Assessments, Children, each with the count of what waits in it", async ({ page }) => {
  await page.goto("/today");
  const menu = page.getByRole("navigation", { name: "Sections" });
  const names = await menu.getByRole("link").allInnerTexts();
  expect(names.map((n) => n.replace(/\s*\d[\d,]*$/, "").trim())).toEqual(TABS);

  let total = 0;
  for (const tab of ["Curriculum", "Assessments", "Children"]) {
    const waiting = (await lines(page, tab)).filter((l) => l.waits).reduce((s, l) => s + l.n, 0);
    expect(await badge(page, tab), `${tab}'s count is its lines on Today`).toBe(waiting);
    total += waiting;
  }
  expect(await badge(page, "Today"), "Today's count is every tab's").toBe(total);

  for (const [tab, heading] of [["Curriculum", "Curriculum"], ["Assessments", "Assessments"], ["Children", "Children"], ["Today", "Today"]]) {
    await menu.getByRole("link", { name: new RegExp(`^${tab}\\b`) }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(menu.getByRole("link", { name: new RegExp(`^${tab}\\b`) })).toHaveAttribute("aria-current", "page");
  }
});

test("Today lists everything that waits, under the tab where it is done, and each line opens that place", async ({ page }) => {
  await page.goto("/today");
  await expect(page.getByText(/For others|For you/)).toHaveCount(0);

  // Assessments: the answers to check, as the page that checks them counts them
  const assessments = await lines(page, "Assessments");
  const toCheck = assessments.find((l) => l.title === "Answers to check")?.n ?? 0;
  if (toCheck) {
    await page.getByRole("region", { name: "Answers to check" }).getByRole("link").first().click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check the answers");
    await expect(page.getByText(`${toCheck} ${toCheck === 1 ? "answer" : "answers"} left to check`)).toBeVisible();
    await page.goto("/today");
  }

  // the test's own class pack, waiting before it prints: its line opens the page that approves exactly that pack
  const pack = page.getByRole("region", { name: "Class papers to approve" }).getByRole("link", { name: new RegExp(SECTION) });
  await expect(pack).toBeVisible();
  await pack.click();
  await expect(page).toHaveURL(new RegExp(`section=${SECTION}&week=${WEEK}&kind=practice`));
  await expect(page.getByRole("button", { name: /Approve/ })).toBeVisible();
  await page.goto("/today");

  // Curriculum: skills to approve, the engine's questions, the topics not taught yet, each counted as the rows say
  const curriculum = Object.fromEntries((await lines(page, "Curriculum")).map((l) => [l.title, l]));
  const [{ drafts }] = await sql<{ drafts: number }[]>`select count(*)::int as drafts from skill_set where status <> 'ratified'`;
  const [{ asks }] = await sql<{ asks: number }[]>`select count(*)::int as asks from ask where answer is null`;
  const [{ off }] = await sql<{ off: number }[]>`select count(*)::int as off from topic t where not exists (select 1 from child k where k.tenant_id = t.tenant_id and k.active and taught_in(t.tenant_id, t.code, k.section))`;
  expect(curriculum["Skills to approve"]?.n ?? 0).toBe(drafts);
  expect(curriculum["Questions the engine drafted for you"]?.n ?? 0).toBe(asks);
  expect(curriculum["Topics not taught yet"]?.n ?? 0).toBe(off);
  expect(curriculum["Topics not taught yet"]?.waits ?? false, "a topic not taught yet is the school's choice, not work waiting").toBe(false);
  for (const [title, heading] of [["Skills to approve", "Approve the skills"], ["Questions the engine drafted for you", "Questions to answer"]]) {
    if (!curriculum[title]) continue;
    await page.getByRole("region", { name: title }).getByRole("link").first().click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await page.goto("/today");
  }

  // Children: the test child's parent report, written and not approved, opens on the report itself
  const report = page.getByRole("region", { name: "Parent reports to approve" }).getByRole("link", { name: new RegExp(`Grade 2 · ${SECTION} · Roll 1`) });
  await expect(report).toBeVisible();
  await report.click();
  await expect(page).toHaveURL(/\/growth\/[0-9a-f-]+\/parent$/);
  await expect(page.getByTestId("parent-report")).toBeVisible();
});

test("an educator sees every line a coordinator sees, and no engineering map", async ({ page }) => {
  await page.goto("/today");
  const coordinator = { a: await lines(page, "Assessments"), c: await lines(page, "Curriculum"), k: await lines(page, "Children") };
  await expect(page.getByRole("complementary").getByRole("link", { name: "How it works" })).toBeVisible();

  await sql`update config set value = value || ${sql.json([EDUCATOR])} where key = 'app.staff'`;
  await signInAs(page, EDUCATOR.email);
  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");
  expect({ a: await lines(page, "Assessments"), c: await lines(page, "Curriculum"), k: await lines(page, "Children") }).toEqual(coordinator);
  await expect(page.getByText(/For others|For you|No one on the staff list/)).toHaveCount(0);
  await expect(page.getByRole("complementary").getByRole("link", { name: "How it works" })).toHaveCount(0);
});

test("weeks and classes on Today are said in words, not codes", async ({ page }) => {
  await page.goto("/today");
  const main = page.getByRole("main");
  await expect(main.getByText(new RegExp(`Grade 2 · ${SECTION} · class practice · ${weekWords(WEEK)}`))).toBeVisible();
  expect(weekWords(WEEK)).toMatch(/^week of \d{1,2} [A-Z][a-z]{2}$/);
  expect(await main.innerText(), "an ISO week code on Today").not.toMatch(/\b\d{4}-W\d{2}\b/);
});
