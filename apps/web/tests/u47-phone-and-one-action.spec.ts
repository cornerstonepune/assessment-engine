/**
 * U47 — On a phone every action is big enough to tap and what needs doing is on the row; on every page one main action
 * (goals/ux8d-phone-and-one-action.yaml). Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we have right now
 * for math, making sure that every screen and every other representation is thought through well: it's clear, it's
 * accurate, clickability is fine."
 *
 * A Grade 2 class of the test's own, made once and kept (evidence is append-only): Asha has enough checked answers for a
 * colour, so a home assessment is proposed for her, and a read paper with an answer waiting; the class has a practice
 * paper this week, planned. Every page is read as the class's educator and as the coordinator.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";
import { SIGNED_IN } from "../playwright.config";
import { isoWeek } from "../lib/week";
import { signIn } from "./sign-in";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U47-CLASS";
const THIS = isoWeek();
const QR = { read: "CS47A001", practice: "CS47A0P1" };
const EDUCATOR = { email: "u47-educator@cornerstone.test", name: "U47 Educator", role: "educator", classes: [SECTION] };
const PHONE = { width: 390, height: 844 };
let kids: Record<string, string>;
let sheet: string;

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina"]);
  const [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  const [skill] = await sql<{ code: string; rung: string }[]>`
    select r.skill_codes[1] as code, r.code as rung from rung r join skill_set ss on ss.rung_code = r.code where ss.code = 'ADD.2D2D'`;
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from evidence_event where child_id = ${kids.Asha}`;
  if (!n) {
    for (const right of [true, true, false, false, true, false, true, false]) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${kids.Asha}, ${skill.code}, ${skill.rung}, ${right}, '{}', 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${kids.Asha}::uuid)`;
  }
  const [ws] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template
    where source = 'library' and retired_at is null and skill_set_code = 'ADD.2D2D' and difficulty = 'Medium' order by code limit 1`;
  ({ sheet } = await aReadPaper(sql, {
    qr: QR.read,
    child: kids.Asha,
    template: ws.id,
    items: ws.item_ids.slice(0, 2),
    reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }],
  }));
  await sql`delete from prescription where child_id = ${kids.Asha} and week = ${THIS} and kind = 'practice'`;
  await sql`delete from sheet_instance where qr_code = ${QR.practice}`;
  const [{ id: practice }] = await sql<{ id: string }[]>`
    insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, section, week, kind, print_status)
    values (${tenant}, ${QR.practice}, ${ws.id}, ${kids.Asha}, ${SECTION}, ${THIS}, 'practice', 'new') returning id`;
  await sql`
    insert into prescription (tenant_id, child_id, week, kind, rule_fired, skill_set_code, difficulty, sheet_instance_id)
    values (${tenant}, ${kids.Asha}, ${THIS}, 'practice', 'band_default', 'ADD.2D2D', 'Medium', ${practice})`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email}) || ${sql.json([EDUCATOR])}
    where key = 'app.staff'`;
});
test.afterAll(async () => {
  await sql`delete from prescription where child_id = ${kids.Asha} and week = ${THIS} and kind = 'practice'`;
  await sql`delete from sheet_instance where qr_code = ${QR.practice}`;
  await sql`
    update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                               where s ->> 'email' <> ${EDUCATOR.email})
    where key = 'app.staff'`;
  await sql.end();
});

async function as(browser: Browser, who: "educator" | "coordinator", viewport?: { width: number; height: number }): Promise<Page> {
  if (who === "coordinator") return (await browser.newContext({ storageState: SIGNED_IN, viewport })).newPage();
  const page = await (await browser.newContext({ storageState: { cookies: [], origins: [] }, viewport })).newPage();
  await signIn(page, EDUCATOR.email);
  await expect(page).toHaveURL(/\/today$/);
  return page;
}

const pages = () => [
  "/today",
  "/",
  "/library",
  "/worksheets",
  "/papers",
  `/papers/approve?section=${SECTION}&week=${THIS}&kind=practice`,
  `/make/${SECTION}`,
  "/capture",
  `/capture/${sheet}`,
  "/growth",
  `/growth/class/${SECTION}`,
  `/growth/${kids.Asha}`,
];

/** The page itself, past its loading screen. */
async function open(page: Page, path: string) {
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText("Loading…");
}

test("every page has one main action at most: the one loud colour, once", async ({ browser }) => {
  test.setTimeout(240_000);
  const loud: string[] = [];
  for (const who of ["educator", "coordinator"] as const) {
    const page = await as(browser, who);
    for (const path of [...pages(), ...(who === "coordinator" ? ["/skill-sets/approve"] : [])]) {
      await open(page, path);
      const found = await page.evaluate(() => {
        const terracotta = getComputedStyle(document.documentElement).getPropertyValue("--terracotta").trim();
        const probe = document.createElement("span");
        probe.style.color = terracotta;
        document.body.append(probe);
        const rgb = getComputedStyle(probe).color;
        probe.remove();
        return [...document.querySelectorAll("main a, main button, main summary, main input[type=submit]")]
          .filter((el) => {
            const b = el.getBoundingClientRect();
            return b.width > 0 && b.height > 0 && getComputedStyle(el).backgroundColor === rgb;
          })
          .map((el) => (el.textContent ?? "").trim().slice(0, 40));
      });
      if (found.length > 1) loud.push(`${who} ${path}: ${found.length} (${found.slice(0, 4).join(" | ")})`);
    }
    await page.context().close();
  }
  expect(loud).toEqual([]);
});

test("on a phone every action is big enough to tap: a button or chip 44 px tall, any other 24 px", async ({ browser }) => {
  test.setTimeout(240_000);
  const small: string[] = [];
  for (const who of ["educator", "coordinator"] as const) {
    const page = await as(browser, who, PHONE);
    for (const path of pages()) {
      await open(page, path);
      const found = await page.evaluate(() => {
        const sel = "main button, main summary, main select, main input:not([type=hidden]), main a.btn, main a.chip, main td > a:only-child";
        return [...document.querySelectorAll(sel)]
          .filter((el) => {
            const b = el.getBoundingClientRect();
            if (!(b.width > 0 && b.height > 0)) return false;
            // a tick box is tapped through its label
            const target = (el as HTMLInputElement).type === "checkbox" || (el as HTMLInputElement).type === "radio" ? (el.closest("label") ?? el) : el;
            const h = target.getBoundingClientRect().height;
            const big = el.matches(".btn, .chip, button.btn, summary.btn");
            return h < (big ? 44 : 24) - 0.5;
          })
          .map((el) => `${el.tagName.toLowerCase()} "${(el.textContent ?? (el as HTMLInputElement).value ?? "").trim().slice(0, 30)}" ${Math.round(el.getBoundingClientRect().height)}px`);
      });
      for (const f of found) small.push(`${who} ${path}: ${f}`);
    }
    await page.context().close();
  }
  expect([...new Set(small)]).toEqual([]);
});

test("on a phone, what needs doing is on the row: an assessment's stage, and why a home assessment works on what it does", async ({ browser }) => {
  const page = await as(browser, "educator", PHONE);
  await open(page, `/make/${SECTION}`);
  // the reason the educator approves on, on the screen, not scrolled off to the side
  const why = page.locator("tr", { hasText: "Asha" }).getByText(/right|mistake|move up/i).first();
  await expect(why).toBeVisible();
  const box = await why.boundingBox();
  expect(box!.x + box!.width, "the reason sits inside the screen").toBeLessThanOrEqual(PHONE.width);
  await open(page, "/papers");
  const stage = page.locator("[data-testid=stage-on-row]").first();
  await expect(stage).toBeVisible();
  const s = await stage.boundingBox();
  expect(s!.x + s!.width, "where an assessment stands sits inside the screen").toBeLessThanOrEqual(PHONE.width);
  await page.context().close();
});

test("the small words: a field says what it asks in full, and the grades are said as a person says them", async ({ browser }) => {
  const page = await as(browser, "educator");
  await open(page, `/make/custom?child=${kids.Asha}`);
  // the field's own words fit inside it: "How m" was "How many" cut short
  const fits = await page.getByLabel("Questions 1").evaluate((el) => {
    const input = el as HTMLInputElement;
    const css = getComputedStyle(input);
    const ctx = document.createElement("canvas").getContext("2d")!;
    ctx.font = `${css.fontWeight} ${css.fontSize} ${css.fontFamily}`;
    const room = input.clientWidth - parseFloat(css.paddingLeft) - parseFloat(css.paddingRight);
    return ctx.measureText(input.placeholder).width <= room;
  });
  expect(fits, "the placeholder fits its field").toBe(true);
  await expect(page.locator("aside")).not.toContainText(/Grade \d+–Grade \d+/i);
  await page.context().close();
});
