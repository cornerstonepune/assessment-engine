/**
 * U43 — On a phone, the heading at the top and every action on screen; one word and one format for dates, weeks,
 * grades and states (goals/ux7-phone-and-words.yaml). Nimish, 2026-10-15: "Most of the pages just have a long list for
 * no reason. All these things should be expandable and collapsible. They should have the right set of columns which are
 * important. It should be teacher-specific."
 *
 * A Grade 2 class of the test's own, made once and kept (evidence is append-only), so every page has something dated,
 * weekly, graded and coloured to say: Asha has a read paper and enough checked answers for a colour; Bina has one answer,
 * too few to say anything; Asha has a home assessment this week and the class a week's practice paper. Every page is read
 * once a person at 400 px, as the class's educator and as the coordinator, and each sentence is checked on what was read.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { SIGNED_IN } from "../playwright.config";
import { isoWeek } from "../lib/week";
import { signIn } from "./sign-in";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U43-CLASS";
const THIS = isoWeek();
const QR = { asha: "CS43A001", home: "CS43A0F1", spare: "CS43C001" };
const EDUCATOR = { email: "u43-educator@cornerstone.test", name: "U43 Educator", role: "educator", classes: [SECTION] };
const PHONE = { width: 400, height: 800 };

/** What one page showed at 400 px. */
type Seen = { path: string; heading: number | null; wide: number; off: string[]; text: string };
const seen: Record<"educator" | "coordinator", Seen[]> = { educator: [], coordinator: [] };

test.beforeAll(async ({ browser }) => {
  test.setTimeout(600_000);
  const kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const [skill] = await sql<{ code: string; rung: string; set: string }[]>`
    select r.skill_codes[1] as code, r.code as rung, ss.code as set from rung r join skill_set ss on ss.rung_code = r.code
    where r.band = 'G2' and cardinality(r.skill_codes) > 0 order by r.ladder_order, ss.code limit 1`;
  for (const [who, answers] of [["Asha", [true, true, true, true, true, true, false, true]], ["Bina", [true]]] as const) {
    const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${kids[who]}`;
    if (n) continue;
    for (const right of answers) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${kids[who]}, ${skill.code}, ${skill.rung}, ${right}, '{}', 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${kids[who]}::uuid)`;
  }
  const [ws] = await sql<{ id: string; item_ids: string[]; code: string }[]>`
    select id, item_ids, code from sheet_template
    where source = 'library' and retired_at is null and band = 'G2' and cardinality(item_ids) >= 2 order by code limit 1`;
  const [had] = await sql`select 1 from sheet_instance where qr_code = ${QR.asha}`;
  if (!had) {
    await aReadPaper(sql, {
      qr: QR.asha,
      child: kids.Asha,
      template: ws.id,
      items: ws.item_ids.slice(0, 2),
      reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
    });
  }
  // Asha's parent report, written: its date shows on her page and on the reports page (its letter, an empty draft, is
  // not read: the parent page is read for Bina, who has none)
  const [{ n: notes }] = await sql<{ n: number }[]>`select count(*)::int as n from parent_note where child_id = ${kids.Asha}`;
  if (!notes) {
    await sql`insert into parent_note (tenant_id, child_id, week, body) values (${tenant}, ${kids.Asha}, ${THIS}, '{"facts": {}, "draft": {}}')`;
  }
  // Asha's home assessment and the class's practice paper, this week
  await sql`delete from sheet_instance where qr_code in ${sql([QR.home, QR.spare])}`;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, kind, print_status)
    values (${tenant}, ${QR.home}, ${ws.id}, ${kids.Asha}, ${THIS}, 'focus', 'new')`;
  await sql`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, section, week, kind, print_status)
    values (${tenant}, ${QR.spare}, ${ws.id}, ${SECTION}, ${THIS}, 'practice', 'new')`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([EDUCATOR])}
    where key = 'app.staff'`;
  const [read] = await sql<{ id: string }[]>`select id from sheet_instance where qr_code = ${QR.asha}`;
  const [item] = await sql<{ item_key: string }[]>`select item_key from item where id = ${ws.item_ids[0]}`;
  const pages = [
    "/today",
    "/",
    "/library",
    `/library/${item.item_key}`,
    "/worksheets",
    "/worksheets/taxonomy",
    `/worksheets/${ws.code}`,
    `/worksheets/${QR.asha}`,
    `/worksheets/${QR.home}`,
    `/skill-sets/${skill.set}`,
    "/skill-sets/approve",
    "/asks",
    "/papers",
    `/papers/approve?section=${SECTION}&week=${THIS}&kind=practice`,
    "/papers/make",
    "/make",
    `/make/${SECTION}`,
    `/make/${SECTION}/week`,
    `/make/custom?child=${kids.Asha}`,
    "/capture",
    `/capture/${read.id}`,
    "/capture/check",
    "/growth",
    `/growth/class/${SECTION}`,
    `/growth/${kids.Asha}`,
    `/growth/${kids.Asha}/report`,
    `/growth/${kids.Bina}/parent`,
    `/growth/${kids.Bina}`,
    "/growth/reports",
  ];
  for (const role of ["educator", "coordinator"] as const) {
    const page = role === "educator" ? await asEducator(browser) : await signedIn(browser);
    for (const path of [...pages, ...(role === "coordinator" ? ["/workflows"] : [])]) seen[role].push(await look(page, path));
    await page.context().close();
  }
});
test.afterAll(async () => {
  // this week's papers go; the class and its read paper stay (evidence is append-only)
  await sql`delete from sheet_instance where qr_code in ${sql([QR.home, QR.spare])}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function asEducator(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] }, viewport: PHONE });
  const page = await context.newPage();
  await signIn(page, EDUCATOR.email);
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

async function signedIn(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: SIGNED_IN, viewport: PHONE });
  return context.newPage();
}

/** One page at 400 px: where its heading's first line ends, how wide the page is, every action outside the screen that
 *  is not inside a table's own scroll, and its words. */
async function look(page: Page, path: string): Promise<Seen> {
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1 }).first(), path).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 }).first(), `${path} could not load`).not.toHaveText("This page could not load");
  return page.evaluate((path) => {
    const h1 = document.querySelector("main h1");
    const r = h1?.getBoundingClientRect();
    const heading = r ? r.top + window.scrollY + parseFloat(getComputedStyle(h1!).lineHeight) : null;
    const scrolls = (el: Element) => {
      for (let p = el.parentElement; p; p = p.parentElement) {
        const o = getComputedStyle(p).overflowX;
        if ((o === "auto" || o === "scroll") && p.scrollWidth > p.clientWidth) return true;
      }
      return false;
    };
    const off = [...document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary")]
      .filter((el) => {
        const b = el.getBoundingClientRect();
        return b.width > 0 && b.height > 0 && (b.right > window.innerWidth + 0.5 || b.left < -0.5) && !scrolls(el);
      })
      .map((el) => `${el.tagName.toLowerCase()} "${(el.textContent ?? "").trim().slice(0, 40)}"`);
    const main = document.querySelector("main") as HTMLElement;
    return { path, heading, wide: document.documentElement.scrollWidth, off, text: main.innerText };
  }, path);
}

const everyPage = () => [...seen.educator.map((s) => ({ ...s, as: "educator" })), ...seen.coordinator.map((s) => ({ ...s, as: "coordinator" }))];

/** Each page's lines matching `re`, as "who path: line". */
function found(re: RegExp): string[] {
  return everyPage().flatMap((s) =>
    s.text
      .split("\n")
      .filter((line) => re.test(line))
      .map((line) => `${s.as} ${s.path}: ${line.trim().slice(0, 120)}`),
  );
}

test("on a phone, every page's heading is in the top 120 px", () => {
  const low = everyPage().filter((s) => s.heading == null || s.heading > 120).map((s) => `${s.as} ${s.path}: ${Math.round(s.heading ?? -1)} px`);
  expect(low).toEqual([]);
});

test("on a phone, no action is off-screen", () => {
  const wide = everyPage().filter((s) => s.wide > PHONE.width).map((s) => `${s.as} ${s.path}: ${s.wide} px wide`);
  expect(wide, "a page scrolls sideways").toEqual([]);
  const off = everyPage().flatMap((s) => s.off.map((o) => `${s.as} ${s.path}: ${o}`));
  expect(off, "an action off the screen").toEqual([]);
});

const MONTH = "(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)";

test("a date is one format on every page", () => {
  expect(seen.coordinator.length).toBeGreaterThan(20);
  // one date at least, in the one format: Asha's paper was read today
  expect(found(new RegExp(`\\b\\d{2}-${MONTH}-\\d{4}\\b`)).length).toBeGreaterThan(0);
  expect(found(/\b\d{4}-\d{2}-\d{2}\b/), "a date written as 2026-10-21").toEqual([]);
  // "21 Oct", "21 October 2026": a date said any other way; a week's own words ("week of 19 Oct") are a week's, and a
  // row's own prose ("the 24 September paper", an ask's question as the seed words it) is the row's
  expect(found(new RegExp(`(?<!week of )\\b\\d{1,2} ${MONTH}\\b(?!-)`)), "a date in another format").toEqual([]);
  expect(found(new RegExp(`\\b\\d{1,2} ${MONTH}[a-z]+ \\d{4}\\b`)), "a date in another format").toEqual([]);
});

test("a week is one format on every page", () => {
  expect(found(/\bweek of \d{1,2} [A-Z][a-z]{2}\b/).length).toBeGreaterThan(0);
  expect(found(/\b\d{4}-W\d{2}\b/), "a week written as 2026-W43").toEqual([]);
});

test("a grade is one word on every page", async () => {
  const grades = await sql<{ code: string; name: string }[]>`select code, name from grade where code <> name`;
  expect(found(/\bGrade 2\b/).length).toBeGreaterThan(0);
  // a grade's code alone, never part of a longer code ("G2-C", "NUM.OPS.01")
  const codes = new RegExp(`(?<![\\w.-])(?:${grades.map((g) => g.code).join("|")})(?![\\w.-])`);
  expect(found(codes), "a grade said by its code").toEqual([]);
});

test("a child's standing is one word on every page", async () => {
  // a colour's row holds two words, for a key and for a count; a page says it with one, the same in both
  const colours = await sql<{ words: string; count_words: string }[]>`select words, count_words from state_colour where words <> count_words`;
  expect(found(/\bsecure\b/i).length).toBeGreaterThan(0);
  for (const c of colours) {
    expect(found(new RegExp(`\\b${c.words}\\b`, "i")), `"${c.words}" where every other page says "${c.count_words}"`).toEqual([]);
  }
});
