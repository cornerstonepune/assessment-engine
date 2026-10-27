/**
 * Results by topic (goals/res_results_by_topic.yaml). Nimish, 24 Oct 2026: "The unit of reference is the topic: Subject,
 * then Topic, then Skill, then difficulty levels." — "Scorecard topic-forward. Class view: topics as rows, children inside.
 * Child page: a row per topic with level, score, strength or weakness." — "Validation is embedded: the child's two or three
 * page images are openable per assessment."
 *
 * The class is tests/results-rows.ts's, made from real papers signed off: on 2-digit + 2-digit Asha is practising (2 right,
 * 1 wrong, 1 wrong with working, 1 blank), Bina is ready to move up and has an answer waiting, Chetan has no paper. Its
 * educator is signed in as the site signs one in; so is the educator of another class.
 */
import { createHmac } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { A, B, MINE, OTHER, SKILL, TOPIC, aResultsClass } from "./results-rows";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
let kids: Record<string, string> = {};
let skillName = "";
let topicName = "";
const BIG = "U71-BIG";
// The time a page may take, on the seeded database (the owner's budget: under a second)
const BUDGET = 1000;

test.beforeAll(async () => {
  test.setTimeout(180_000);
  ({ kids } = await aResultsClass(sql));
  [{ name: skillName }] = await sql<{ name: string }[]>`select name from skill where code = ${SKILL}`;
  [{ name: topicName }] = await sql<{ name: string }[]>`select name from topic where code = ${TOPIC}`;
});
test.afterAll(async () => sql.end());

/** A member of staff signed in, as the site signs one in. */
async function as(browser: Browser, email: string): Promise<Page> {
  const body = `${Buffer.from(email).toString("base64url")}.${Date.now() + 3_600_000}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  const context = await browser.newContext({ baseURL: "http://localhost:3100", viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
  return context.newPage();
}

const topicRow = (page: Page, code = TOPIC) => page.locator(`tr[data-topic="${code}"]`);
const skillRow = (page: Page, code = SKILL) => page.locator(`tr[data-skill="${code}"]`);
const childRow = (page: Page, who: string) => page.locator(`tr[data-child="${kids[who]}"]`);

test("class results open on the educator's own class: subjects, then topics, folded, each topic counted in words", async ({ browser }) => {
  const page = await as(browser, MINE.email);
  await page.goto("/growth");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Class results");
  // the class is chosen in the page's own filter row, and it opens on the educator's own
  await expect(page.locator("[data-filterbar]").getByLabel("Class")).toHaveValue(A);
  // grouped by subject, then a row per topic
  const [{ subject }] = await sql<{ subject: string }[]>`
    select coalesce(s.label, s.name) as subject from topic t join subject s on s.code = t.subject_code where t.code = ${TOPIC}`;
  await expect(page.getByRole("heading", { name: subject })).toBeVisible();
  const row = topicRow(page);
  await expect(row).toContainText(topicName);
  // each count in words beside its number, never a colour alone: one secure, one practising, one not assessed yet
  await expect(row).toContainText("1 secure");
  await expect(row).toContainText("1 practising");
  await expect(row).toContainText("1 not assessed yet");
  await expect(row.locator("[data-label='Last assessed']")).not.toHaveText("");
  // folded: no skill and no child shows until the topic is opened
  await expect(page.locator("tr[data-skill]")).toHaveCount(0);
  await expect(page.locator("tr[data-child]")).toHaveCount(0);
  await expect(row.getByRole("link", { name: topicName })).toHaveAttribute("aria-expanded", "false");
  await page.context().close();
});

test("a topic opens to its skills and a skill to its children, each with level and state", async ({ browser }) => {
  const page = await as(browser, MINE.email);
  await page.goto("/growth");
  await topicRow(page).getByRole("link", { name: topicName }).click();
  await expect(topicRow(page).getByRole("link", { name: topicName })).toHaveAttribute("aria-expanded", "true");
  const skill = skillRow(page);
  await expect(skill).toContainText(skillName);
  await expect(skill).toContainText("2 at Medium");
  await expect(page.locator("tr[data-child]")).toHaveCount(0);
  await skill.getByRole("link", { name: skillName }).click();
  const asha = childRow(page, "Asha");
  await expect(asha).toContainText("Medium");
  await expect(asha.locator("[data-status]")).toHaveText("practising");
  // right of attempted, and the three signals apart: a blank is never wrong
  await expect(asha).toContainText("2 of 4 right");
  await expect(asha).toContainText("1 wrong");
  await expect(asha).toContainText("1 wrong with working");
  await expect(asha).toContainText("1 blank");
  await expect(childRow(page, "Bina").locator("[data-status]")).toHaveText("secure");
  // a child with answers still waiting is told so, with the way to check them
  const waits = childRow(page, "Bina").getByRole("link", { name: "1 answer waiting to be checked: results may change" });
  await expect(waits).toHaveAttribute("href", `/growth/${kids.Bina}#needs-you`);
  await expect(childRow(page, "Chetan")).toContainText("not assessed yet");
  // who needs the educator first; nothing checked last
  await expect(page.locator("tr[data-child]").last()).toHaveAttribute("data-child", kids.Chetan);
  await page.context().close();
});

test("an opened topic says its assessments by kind: the class assessment, home assessments and for how many children, practice", async ({ browser }) => {
  const page = await as(browser, MINE.email);
  await page.goto(`/growth?class=${A}&topic=${TOPIC}`);
  const flow = page.getByTestId("topic-papers");
  await expect(flow).toContainText("1 class assessment, for 2 children");
  await expect(flow).toContainText("2 home assessments, for 1 child");
  await page.context().close();
});

test("a child's page is a row per topic: level, last score in three signals, state, strength or weakness", async ({ browser }) => {
  const page = await as(browser, MINE.email);
  await page.goto(`/growth/${kids.Asha}`);
  const row = page.getByRole("table", { name: "Topics" }).locator(`tr[data-topic="${TOPIC}"]`);
  await expect(row).toContainText(topicName);
  await expect(row.locator("[data-label='Level']")).toHaveText("Medium");
  await expect(row).toContainText("2 of 4 right");
  await expect(row).toContainText("1 wrong with working");
  await expect(row).toContainText("1 blank");
  await expect(row.locator("[data-status]")).toHaveText("practising");
  await expect(row).toContainText(`Weakest: ${skillName}, 2 of 4 right`);
  await page.goto(`/growth/${kids.Bina}`);
  const bina = page.getByRole("table", { name: "Topics" }).locator(`tr[data-topic="${TOPIC}"]`);
  await expect(bina).toContainText(`Strongest: ${skillName}, 10 of 11 right`);
  await expect(page.getByRole("link", { name: "1 answer waiting to be checked: results may change" })).toBeVisible();
  // the move-a-child section still sits on the page
  await expect(page.getByRole("heading", { name: /Grade and class/ })).toBeVisible();
  await page.context().close();
});

test("an assessment opens the child's written page in place", async ({ browser }) => {
  const page = await as(browser, MINE.email);
  await page.goto(`/growth/${kids.Asha}`);
  await page.getByRole("table", { name: "Topics" }).locator(`tr[data-topic="${TOPIC}"]`).getByRole("link", { name: topicName }).click();
  const paper = page.locator('[data-paper="CSU71A01"]');
  await expect(paper).toContainText("class assessment");
  const [{ capture }] = await sql<{ capture: string }[]>`
    select c.id as capture from capture c join sheet_instance si on si.id = c.sheet_instance_id
    where si.qr_code = 'CSU71A01' and c.superseded_by is null`;
  const shown = page.waitForResponse((r) => r.url().includes(`/api/scan/${capture}/1`));
  await paper.getByText(/See the child.s page/).click();
  const img = paper.getByRole("img", { name: /Asha's written page 1/ });
  await expect(img).toBeVisible();
  expect((await shown).status()).toBe(200);
  await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBeGreaterThan(0);
  // still the child's page: nothing was left
  expect(new URL(page.url()).pathname).toBe(`/growth/${kids.Asha}`);
  await page.context().close();
});

test("a teacher of another class is refused the class and its children, in words, and opens on their own", async ({ browser }) => {
  const page = await as(browser, OTHER.email);
  await page.goto("/growth");
  await expect(page.locator("[data-filterbar]").getByLabel("Class")).toHaveValue(B);
  await expect(page.locator("[data-filterbar]").getByLabel("Class").locator(`option[value="${A}"]`)).toHaveCount(0);
  for (const url of [`/growth?class=${A}`, `/growth?class=${A}&topic=${TOPIC}&skill=${SKILL}`, `/growth/${kids.Asha}`]) {
    await page.goto(url);
    await expect(page.getByText(/is not one of your classes/), url).toBeVisible();
    await expect(page.getByText("Asha"), url).toHaveCount(0);
  }
  await page.context().close();
});

test("class results, an open topic, an open skill and a child's page each open within a second on a class of 40", async ({ page }) => {
  test.setTimeout(240_000);
  // forty children, each with a state on every skill of their grade: what a full class looks like to the page
  const names = Array.from({ length: 40 }, (_, i) => `Big ${i + 1}`);
  const big = await sql<{ id: string }[]>`select id from child where section = ${BIG}`;
  if (!big.length) {
    const { aClass } = await import("./rows");
    const ids = Object.values(await aClass(sql, BIG, "G2", names));
    const states = ["patterned_error", "emerging", "practising", "secure", "stretch_ready", "not_enough_yet"];
    await sql`
      insert into child_skill_state (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, last_seen)
      select c.tenant_id, c.id, s.registry_codes[1], s.rung_code, (${states}::text[])[1 + (abs(hashtext(c.id::text || s.code)) % 6)], 6, 4, now()
      from child c cross join skill s where c.id = any(${ids}::uuid[]) and s.grade = 'G2'
      on conflict do nothing`;
    await sql`analyze child_skill_state`;
  }
  const [{ id: child }] = await sql<{ id: string }[]>`select id from child where section = ${BIG} order by roll_order(roll_no) limit 1`;
  const urls = [
    `/growth?class=${BIG}`,
    `/growth?class=${BIG}&topic=${TOPIC}`,
    `/growth?class=${BIG}&topic=${TOPIC}&skill=${SKILL}`,
    `/growth/${child}`,
  ];
  for (const url of urls) {
    await page.goto(url); // the build's first request of a page warms its own code, once
    const times: number[] = [];
    for (let k = 0; k < 3; k++) {
      const t = Date.now();
      await page.goto(url);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      times.push(Date.now() - t);
    }
    const median = times.sort((x, y) => x - y)[1];
    console.log(`u71 | ${url} | ${median} ms`);
    expect(median, url).toBeLessThan(BUDGET);
  }
});
