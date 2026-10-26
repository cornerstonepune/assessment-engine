/**
 * S41 — the subject, the class and the search at the top of every screen; Today's five lines; a phone
 * (goals/s1-subject-class-and-today.yaml). Slice S1 of the scope Nimish locked on 2026-10-22, from the flow map: "At the
 * top of every screen: Subject ▾ (Maths, English, …) · Class ▾ (G1, G2, … or every class) · a search box that finds a
 * child, an assessment or a paper code."
 *
 * A Grade 2 class of the test's own, made once and kept (evidence is append-only): Asha secure on one skill and with a
 * paper read this week (one answer settled, one waiting for a person); Bina wrong on two skills with the same named
 * mistake each time, so she needs help on both; Chetan with nothing yet. The five lines are read for that class alone,
 * so every number is the test's own.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { SIGNED_IN } from "../playwright.config";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "S41-CLASS";
const OTHER = "S41-OTHER";
const QR = "CS41A001";
let kids: Record<string, string> = {};
let setName = "";
let mistake = "";

test.beforeAll(async () => {
  test.setTimeout(120_000);
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan"]);
  await aClass(sql, OTHER, "G3", ["Dev"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const skills = await sql<{ code: string; rung: string }[]>`
    select ss.registry_codes[1] as code, ss.rung_code as rung from skill ss
    where ss.grade = 'G2' and cardinality(ss.registry_codes) > 0 order by ss.ladder_order, ss.code limit 2`;
  const [m] = await sql<{ code: string; name: string }[]>`select code, name from misconception order by code limit 1`;
  mistake = m.name;
  const evidence = async (child: string, skill: { code: string; rung: string }, right: boolean, n: number) => {
    for (let i = 0; i < n; i++) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${child}, ${skill.code}, ${skill.rung}, ${right}, ${right ? sql`'{}'` : sql`array[${m.code}]`},
                'item', now(), 'e2e')`;
    }
  };
  // this week's evidence, once a week: last week's rows stay, append-only, and this week's are written afresh
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from evidence_event where child_id = ${kids.Bina} and observed_at >= date_trunc('week', now())`;
  if (!n) {
    await evidence(kids.Asha, skills[0], true, 4);
    await evidence(kids.Bina, skills[0], false, 3);
    await evidence(kids.Bina, skills[1], false, 3);
  }
  for (const id of [kids.Asha, kids.Bina]) await sql`select rebuild_child_skill_state(${id}::uuid)`;
  const [ws] = await sql<{ id: string; item_ids: string[]; set: string }[]>`
    select t.id, t.item_ids, s.name as set from sheet_template t join skill s on s.code = t.skill_set_code
    where t.source = 'library' and t.retired_at is null and t.band = 'G2' and cardinality(t.item_ids) >= 2 order by t.code limit 1`;
  setName = ws.set;
  // read again this week, so the paper is this week's: the reader supersedes the earlier scan, as it does on live
  await aReadPaper(sql, {
    qr: QR,
    child: kids.Asha,
    template: ws.id,
    items: ws.item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  });
  await sql`update sheet_instance set section = ${SECTION}, kind = 'practice', week = to_char(now(), 'IYYY-"W"IW') where qr_code = ${QR}`;
});
test.afterAll(async () => {
  await sql.end();
});

type P = import("@playwright/test").Page;
const find = (page: P) => page.getByRole("search", { name: "Find a child or paper" });

test("every screen opens with the search in the bar, above the heading, and no Class or Subject box (goals/nav3_what_needs_doing.yaml)", async ({ page }) => {
  for (const path of ["/today", "/", "/papers", "/growth", "/capture", "/worksheets", `/growth/${kids.Asha}`]) {
    await page.goto(path);
    await expect(page.locator("[data-viewing], #bar-subject, #bar-class"), path).toHaveCount(0);
    await expect(find(page).getByRole("searchbox"), path).toBeVisible();
    // the bar sits above the page's heading
    const b = (await find(page).boundingBox())!;
    const h = (await page.getByRole("heading", { level: 1 }).first().boundingBox())!;
    expect(b.y + b.height, path).toBeLessThanOrEqual(h.y);
  }
});

test("the search finds a child, an assessment and a paper by its code", async ({ page }) => {
  await page.goto("/today");
  const box = find(page).getByRole("searchbox");
  const found = page.getByRole("list", { name: "Found" });

  await box.fill("Bina");
  await box.press("Enter");
  await expect(found.getByRole("link", { name: new RegExp(`Bina.*${SECTION}`) })).toBeVisible();
  // the name is never in an address: a server logs addresses
  expect(page.url()).not.toContain("Bina");
  await found.getByRole("link", { name: new RegExp(`Bina.*${SECTION}`) }).click();
  await expect(page).toHaveURL(new RegExp(`/growth/${kids.Bina}$`));

  await find(page).getByRole("searchbox").fill(QR.toLowerCase());
  await find(page).getByRole("searchbox").press("Enter");
  await page.getByRole("list", { name: "Found" }).getByRole("link", { name: new RegExp(QR) }).click();
  await expect(page).toHaveURL(new RegExp(`/worksheets/${QR}$`));

  await find(page).getByRole("searchbox").fill(setName.slice(0, 12));
  await find(page).getByRole("searchbox").press("Enter");
  const assessment = page.getByRole("list", { name: "Found" }).getByRole("link", { name: new RegExp(`${SECTION}`) }).first();
  await expect(assessment).toContainText("Assessment");
  await assessment.click();
  await expect(page).toHaveURL(/\/papers\?/);
  await expect(page.getByRole("main")).toContainText(setName);

  await find(page).getByRole("searchbox").fill("zzqqxx-no-such-thing");
  await find(page).getByRole("searchbox").press("Enter");
  await expect(page.getByRole("status").filter({ hasText: "Nothing found" })).toBeVisible();
});

test("Today opens on five lines of what the system knows this week, then the next actions", async ({ page }) => {
  await page.goto(`/today?class=${SECTION}`);
  // folded under the list (goals/nav_teacher_scope_and_todo.yaml): opened to read
  const note = page.locator("details[data-know]");
  await note.locator("summary").click();
  await expect(note).toBeVisible();
  const lines = note.getByRole("listitem");
  await expect(lines).toHaveCount(5);
  // every number is the class's own, counted by code
  await expect(lines.nth(0)).toHaveText(/1 paper came back this week, and 2 answers were read/);
  await expect(lines.nth(1)).toHaveText(/1 answer waits for a person/);
  await expect(lines.nth(2)).toHaveText(/1 of 3 children is secure on a skill; 1 needs help/);
  await expect(lines.nth(3)).toContainText(mistake);
  await expect(lines.nth(3)).toHaveText(/1 child/);
  await expect(lines.nth(4)).toHaveText(/1 child needs help on two or more skills/);
  // the table of what to do comes first and the note under it; a row opens the place it is done
  const n = (await note.boundingBox())!;
  const group = page.locator("details[data-group=answers]");
  await group.locator("summary").click();
  const check = page.locator("tr[data-kind=check]").filter({ hasText: SECTION });
  await expect(check.getByRole("link", { name: "Check this paper" })).toBeVisible();
  expect((await check.boundingBox())!.y).toBeLessThan(n.y);
});

test("on a phone the bar and the heading are at the top and every tap is big enough", async ({ browser }) => {
  const context = await browser.newContext({ storageState: SIGNED_IN, viewport: { width: 400, height: 800 } });
  const page = await context.newPage();
  try {
    for (const path of ["/today", "/papers", "/growth", "/"]) {
      await page.goto(path);
      const top = (await page.getByRole("banner").first().boundingBox())!;
      expect(top.y, path).toBeLessThan(8);
      const h1 = page.getByRole("heading", { level: 1 }).first();
      const end = await h1.evaluate((el) => el.getBoundingClientRect().top + parseFloat(getComputedStyle(el).lineHeight));
      expect(end, `${path}: heading's first line ends at ${end}`).toBeLessThanOrEqual(160);
      // the groups fold into the menu button on a phone; the button and the search are each big enough
      await expect(page.getByRole("navigation", { name: "Sections" })).toBeHidden();
      for (const field of [page.getByRole("button", { name: "Menu" }), find(page).getByRole("searchbox")]) {
        expect((await field.boundingBox())!.height, path).toBeGreaterThanOrEqual(44);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(400);
    }
    // and the menu button opens every page, each one a big tap
    await page.goto("/today");
    await page.getByRole("button", { name: "Menu" }).click();
    for (const link of await page.getByRole("dialog", { name: "Menu" }).getByRole("link").all()) expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  } finally {
    await context.close();
  }
});
