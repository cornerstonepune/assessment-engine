/**
 * U49 — one role for now (goals/ux9c-one-role.yaml). Nimish, 2026-10-22: "Achal sir is the educator coordinator right
 * now. Just keep all the features available for both educators and coordinators for now. As we become bigger, we'll
 * have that bifurcation, so don't differentiate that."
 *
 * An educator of one class of the test's own, and the coordinator (the suite's own sign-in), open the same pages: every
 * page the menu, Today and the class pages lead to, another class's and its child's among them. On each, every action
 * the coordinator is offered — each button, link, field and column, whether a section is open or folded — the educator
 * is offered too, and no page refuses them. Their own class and grade are where pages open; "Every class" in the
 * bar at the top, one choice, shows every class as the coordinator sees them, and that is what is compared.
 */
import { scryptSync } from "node:crypto";
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { TEST_STAFF } from "./global-setup";
import { aClass, aWaitingSkill } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const MINE = "U49-MINE";
const OTHER = "U49-OTHER";
// not mapped to a class, so the same pages open on every class as the coordinator's: the test is about what is offered, not the data
const EDUCATOR = { email: "u49-educator@cornerstone.test", name: "U49 Educator", role: "educator", classes: [] as string[] };
const PASSWORD = "u49-a-long-test-password";
const SALT = "00112233445566778899aabbccddeeff";
const others = sql`(select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s where s ->> 'email' <> ${EDUCATOR.email})`;
let pages: string[] = [];

test.beforeAll(async () => {
  await aClass(sql, MINE, "G2", ["Ira", "Jai"]);
  const other = await aClass(sql, OTHER, "G3", ["Kavi", "Lata"]);
  const password = `scrypt$${SALT}$${scryptSync(PASSWORD, SALT, 64).toString("hex")}`;
  await sql`update config set value = ${others} || ${sql.json([{ ...EDUCATOR, password }])} where key = 'app.staff'`;
  const [{ code: draft }] = await sql<{ code: string }[]>`select code from skill order by status = 'ratified', code limit 1`;
  pages = [
    // a page that opens on the person's own grade is compared at "Every grade", its one tap
    "/today", "/", "/papers", "/growth", "/asks", "/library?grade=all", "/worksheets?grade=all", "/worksheets/taxonomy", "/skill-sets/approve",
    `/skill-sets/${draft}`, "/capture", "/capture/check", "/make", `/make/${OTHER}`, "/papers/approve", "/growth/reports",
    `/growth/class/${OTHER}`, `/growth/${other.Kavi}`, `/growth/${other.Kavi}/report`, "/workflows",
  ];
});
test.afterAll(async () => {
  await sql`update config set value = ${others} where key = 'app.staff'`;
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

/** Every action a page offers, open or folded: buttons, links (by where they go), fields and table columns. The
 *  account's own line (whose classes the menu says) is the person's, not an action. */
async function offered(page: Page, at: string, name: string): Promise<{ refused: boolean; actions: string[] }> {
  await page.goto(at);
  await page.waitForLoadState("networkidle");
  // every section folded open, so what a tap would show is counted: details, and toggles a page draws itself
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => document.querySelectorAll("main details:not([open])").forEach((d) => d.setAttribute("open", "")));
    const closed = page.locator("main [aria-expanded=false]");
    for (let n = await closed.count(); n > 0; n--) await closed.first().click().catch(() => undefined);
  }
  return page.evaluate((name) => {
    // an action said in the person's own name ("as U49 Educator") is the same action for each of them
    const words = (e: Element) => (e.getAttribute("aria-label") ?? e.textContent ?? "").replace(/\s+/g, " ").trim().replaceAll(name, "<person>").replace(/^[▸▾]/, "");
    const out = new Set<string>();
    // the one exception to "don't differentiate": a child's "Grade and class" is the coordinator's alone (Nimish, 27 Oct 2026,
    // goals/mov_move_a_child.yaml; its own spec, u70, proves what a teacher is and is not given there)
    const counted = (e: Element) => !e.closest("#grade-class");
    document.querySelectorAll("main button, main [role=button], main summary").forEach((e) => counted(e) && out.add(`button: ${words(e)}`));
    document.querySelectorAll("a[href]").forEach((e) => counted(e) && out.add(`link: ${new URL((e as HTMLAnchorElement).href).pathname}`));
    document.querySelectorAll("main input:not([type=hidden]), main select, main textarea").forEach((e) =>
      counted(e) && out.add(`field: ${e.getAttribute("name") ?? e.getAttribute("aria-label") ?? ""}`),
    );
    document.querySelectorAll("main th").forEach((e) => out.add(`column: ${words(e)}`));
    const text = document.querySelector("main")?.textContent ?? "";
    return { refused: /not one of your classes|is not yours to take|the coordinator approves/i.test(text), actions: [...out].sort() };
  }, name);
}

test("an educator reaches every page and every action the coordinator does", async ({ browser, page }) => {
  test.setTimeout(300_000);
  const educator = await asEducator(browser);
  try {
    for (const at of pages) {
      const theirs = await offered(page, at, TEST_STAFF.name);
      const mine = await offered(educator, at, EDUCATOR.name);
      // a page's own words may name the coordinator (the map does); a refusal is one the coordinator is not given
      expect(mine.refused, `${at} refuses an educator`).toBe(theirs.refused);
      expect(theirs.actions.filter((a) => !mine.actions.includes(a)), `on ${at}, offered to the coordinator only`).toEqual([]);
    }
  } finally {
    await educator.context().close();
  }
});

test("an educator takes a decision once the coordinator's alone: approving a skill", async ({ browser }) => {
  // a skill waiting for approval (`aWaitingSkill`), put back as it was after
  const [waiting] = await sql<{ code: string }[]>`select code from skill order by code limit 1`;
  const putBack = await aWaitingSkill(sql, waiting.code);
  const educator = await asEducator(browser);
  try {
    await educator.goto("/today");
    await expect(educator.getByRole("main")).toContainText("Skills to approve");
    await educator.getByRole("button", { name: "Menu" }).click();
    await expect(educator.getByRole("dialog", { name: "Menu" }).getByRole("link", { name: "How it works" }), "the engineering map is theirs too").toBeVisible();
    await educator.goto(`/skill-sets/${waiting.code}`);
    await expect(educator.getByRole("button", { name: /^Approve, as / })).toBeVisible();
    await educator.goto("/skill-sets/approve");
    await expect(educator.getByRole("main")).not.toContainText("The coordinator approves the skills");
  } finally {
    await educator.context().close();
    await putBack();
  }
});
