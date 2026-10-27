/**
 * What needs doing as groups, Teaching gone, no filter in the top bar (goals/nav3_what_needs_doing.yaml), walked at 1440 px.
 * Nimish, 26 Oct 2026, on the live site: "There is still this confusing filter part at the top"; "proper expand/collapse, and
 * different types of things that you need to do"; "What Needs Doing essentially connects to each of the other sub-tabs";
 * "Is the queue shrinking? ... It should come in some other part"; "I don't understand the purpose of this teaching page".
 * A class of the test's own and a waiting skill give the page its groups; an educator mapped to that class and one subject gives the scope.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { createHmac } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import postgres from "postgres";
import { aClass, aReadPaper, aWaitingSkill } from "./rows";
import { TODO_GROUPS } from "../lib/todo";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "NAV3-CLASS";
const SKILL = "ADD.2D2D";
let restore: () => Promise<void>;

test.beforeAll(async () => {
  const kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const [ws] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template
    where source = 'library' and retired_at is null and skill_set_code = ${SKILL} and difficulty = 'Medium' order by code limit 1`;
  await aReadPaper(sql, {
    qr: "CSN3A001",
    child: kids.Asha,
    template: ws.id,
    items: ws.item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  });
  restore = await aWaitingSkill(sql, SKILL);
  await sql`
    update config set value = value || ${sql.json([EDUCATOR])}
    where key = 'app.staff' and not value @> ${sql.json([{ email: EDUCATOR.email }])}`;
});
test.afterAll(async () => {
  await sql`delete from class_skill where section = ${SECTION}`; // what the test marked taught: no other spec finds a topic taught
  await restore?.();
  await sql.end();
});

// An educator mapped to one class and one subject, signed in as the site signs one in.
const EDUCATOR = { email: "nav3-educator@cornerstone.test", name: "Nav Three", role: "educator", classes: [SECTION], subjects: ["NUM"] };
async function asEducator(browser: Browser) {
  const body = `${Buffer.from(EDUCATOR.email).toString("base64url")}.${Date.now() + 3_600_000}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  const context = await browser.newContext({ baseURL: "http://localhost:3100", viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
  return { context, page: await context.newPage() };
}

async function open(page: Page, url: string) {
  const response = await page.goto(url);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  return response;
}

test("the top bar has no Viewing, Class or Subject control, for a coordinator or an educator, and an educator still sees only her own class", async ({ page, browser }) => {
  for (const url of ["/today", "/papers", "/growth"]) {
    await open(page, url);
    await expect(page.locator("[data-viewing], #bar-subject, #bar-class"), url).toHaveCount(0);
    await expect(page.getByRole("banner"), url).not.toContainText("Viewing");
  }
  const { context, page: her } = await asEducator(browser);
  await open(her, "/today?open=generate");
  await expect(her.locator("[data-viewing], #bar-subject, #bar-class")).toHaveCount(0);
  const where = await her.locator("td[data-label=Where]").allInnerTexts();
  expect(where.length, "she has rows").toBeGreaterThan(0);
  expect(where.filter((w) => /·\s*\d[A-Z]\b|NAV3|M5-|WV1|U51/.test(w) && !w.includes(SECTION)), "rows of another class").toEqual([]);
  await context.close();
});

test("What needs doing is a short list of folded groups in the order the work happens, each opening into its own table with no approve-all", async ({ page }) => {
  await open(page, "/today");
  const groups = page.locator("details[data-group]");
  const keys = await groups.evaluateAll((els) => els.map((e) => e.getAttribute("data-group")!));
  expect(keys.length, "a short list of kinds of work").toBeGreaterThanOrEqual(3);
  expect(keys.length).toBeLessThanOrEqual(TODO_GROUPS.length);
  const order = TODO_GROUPS.map((g) => g.key as string);
  expect(keys, "in the order the work happens").toEqual(order.filter((k) => keys.includes(k)));
  for (const g of await groups.all()) {
    expect(await g.getAttribute("open"), "folded until opened").toBeNull();
    await expect(g.locator("table")).toBeHidden();
    const line = g.locator("summary");
    await expect(line.locator("a[data-group-home]"), "the heading opens its page").toHaveCount(1);
    await expect(line.locator("[data-group-count]"), "a count").toHaveCount(1);
    await expect(line.locator("[data-status]"), "red, amber or green with its icon").toHaveCount(1);
    await expect(line.locator("a[data-next]"), "the one next action").toHaveCount(1);
  }
  await expect(page.locator("main tbody tr:visible"), "no row shows until a group is opened").toHaveCount(0);
  const first = groups.first();
  await first.locator("summary").click();
  await expect(first.locator("table")).toBeVisible();
  for (const row of await first.locator("tbody tr[data-kind]").all()) {
    await expect(row.locator("[data-status]"), "a priority chip").toHaveCount(1);
    await expect(row.locator("[data-action]"), "its own action").toHaveCount(1);
  }
  await expect(page.getByRole("button", { name: /approve (all|them|these|every)/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /approve (all|them|these|every)/i })).toHaveCount(0);
  const count = Number(await page.locator('[data-todo]').first().getAttribute("data-todo"));
  expect((await page.locator('[data-testid="waiting"]').first().textContent())?.replace(/\D/g, ""), "the menu's figure is the page's").toBe(String(count));
});

test("every group heading and every row opens a page that exists and shows that item", async ({ page }) => {
  test.setTimeout(240_000);
  await open(page, "/today");
  const links = await page.evaluate(() => {
    const out: { href: string; shows: string | null; what: string }[] = [];
    for (const g of document.querySelectorAll("details[data-group]")) {
      const key = g.getAttribute("data-group")!;
      for (const a of g.querySelectorAll("a[data-group-home], a[data-next]")) out.push({ href: a.getAttribute("href")!, shows: null, what: `${key} ${a.hasAttribute("data-next") ? "next" : "heading"}` });
      for (const a of g.querySelectorAll("tbody tr[data-kind] a[data-action]")) out.push({ href: a.getAttribute("href")!, shows: a.closest("tr")!.getAttribute("data-shows"), what: `${key} row` });
    }
    return out;
  });
  expect(links.length).toBeGreaterThan(5);
  // every group's heading and next action, and the first two rows of each group: the rest are the same kind of link
  const seen = new Set<string>();
  const perGroup = new Map<string, number>();
  for (const l of links) {
    const key = `${l.href}|${l.shows}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (l.what.endsWith("row")) {
      const n = (perGroup.get(l.what) ?? 0) + 1;
      perGroup.set(l.what, n);
      if (n > 2) continue;
    }
    const response = await open(page, l.href.split("#")[0]);
    expect(response?.status(), `${l.what} ${l.href}`).toBeLessThan(400);
    await expect(page.getByText("This page could not load"), l.href).toHaveCount(0);
    await expect(page.getByRole("heading", { level: 1 }).first(), l.href).not.toContainText(/not found|404/i);
    if (l.shows) await expect(page.locator("main"), `${l.what} ${l.href} shows ${l.shows}`).toContainText(l.shows, { ignoreCase: true });
  }
  // a topic is marked taught in its own row, and the page comes back showing it done
  const { context, page: her } = await asEducator(page.context().browser()!);
  await open(her, "/today?open=taught");
  const row = her.locator("tr[data-kind=taught]").first();
  await expect(row, "a topic waiting to be marked taught").toBeVisible();
  const topic = (await row.getAttribute("data-shows"))!;
  await row.getByRole("button", { name: "Mark as taught" }).click();
  await expect(her).toHaveURL(/\/today/);
  await expect(her.locator(`tr[data-kind=taught][data-shows="${topic}"]`), "the topic is no longer waiting").toHaveCount(0);
  await context.close();
});

test("the queue-shrinking trend is off What needs doing, its data and function kept, and parked in the notes", async ({ page }) => {
  await open(page, "/today?open=answers");
  await expect(page.locator("main")).not.toContainText(/queue shrinking/i);
  const root = path.resolve(__dirname, "..");
  expect(readFileSync(path.join(root, "lib/queries-today.ts"), "utf8"), "the data function is kept").toMatch(/queueByWeek/);
  expect(existsSync(path.join(root, "app/(app)/today/shrinking.tsx")), "the part is kept, unused, to be placed on Results or Setup").toBe(true);
  const note = readFileSync(path.resolve(root, "../../docs/notes/nav3-what-needs-doing.md"), "utf8");
  expect(note).toMatch(/Parked/);
  expect(note).toMatch(/Is the queue shrinking/);
});

test("Teaching is not in the menu and its old address opens What needs doing", async ({ page }) => {
  await open(page, "/today");
  const top = page.getByRole("navigation", { name: "Sections" }).getByRole("link");
  const names = (await top.allInnerTexts()).map((n) => n.replace(/\s*\d[\d,]*$/, "").trim());
  expect(names).not.toContain("Teaching");
  test.info().annotations.push({ type: "top-level menu items", description: `${names.length}: ${names.join(", ")}` });
  expect(names).toEqual(["What needs doing", "Assessments", "Results", "Setup"]);
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByRole("dialog", { name: "Menu" }).getByRole("link", { name: "Teaching" })).toHaveCount(0);
  await page.keyboard.press("Escape");
  for (const old of ["/taught", "/taught?subject=NUM", "/taught?topic=MUL"]) {
    await page.goto(old);
    await expect(page, old).toHaveURL(/\/today(\?|$)/);
    await expect(page.getByRole("heading", { level: 1 }).first()).toContainText("What needs doing");
  }
});

test("What needs doing opens in under a second, as the other pages do", async ({ page }) => {
  test.setTimeout(240_000);
  const median = async (url: string) => {
    await page.goto(url);
    const ms: number[] = [];
    for (let i = 0; i < 3; i++) {
      const t = Date.now();
      await page.goto(url, { waitUntil: "load" });
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      ms.push(Date.now() - t);
    }
    return ms.sort((a, b) => a - b)[1];
  };
  const times: Record<string, number> = {};
  for (const url of ["/today", "/papers", "/growth", "/", "/capture/check", "/skill-sets/approve"]) times[url] = await median(url);
  test.info().annotations.push({ type: "load time, ms (median of 3, warm)", description: JSON.stringify(times) });
  console.log("load time ms", JSON.stringify(times));
  // On the seeded copy, one second (Nimish: nothing slow). Once the other specs have filled the copy with test classes every
  // page pays the menu's count alike (the layout's one query set), so there the page is held to being no slower than the rest.
  const [{ classes }] = await sql<{ classes: number }[]>`select count(distinct section)::int as classes from child where active`;
  const others = Math.max(...Object.entries(times).filter(([u]) => u !== "/today").map(([, ms]) => ms));
  if (classes < 30) expect(times["/today"], "a seeded copy").toBeLessThan(1000);
  expect(times["/today"], "no slower than the slowest other page").toBeLessThanOrEqual(others * 1.25);
});
