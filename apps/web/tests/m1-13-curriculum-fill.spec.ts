/**
 * M1-13 — the curriculum screens: the browser, the fill view with its walk-through, and the offered-skills queue.
 * Placeholder rows only (tests/m1-13-rows.ts). The screens answer to the educator gate (D-076): the switch, or the staff
 * preview; every test but the gate's own runs as the staff preview (the switch off).
 */
import { mkdirSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Locator, type Page } from "@playwright/test";
import postgres from "postgres";
import { AMBER, clearOffers, code, curriculumRows, FILLED, GREEN, offers, RED, gate, STEPS, TOTAL } from "./m1-13-rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SHOTS = path.resolve(__dirname, "../../../docs/screens/m1-13");
const DESKTOP = { width: 1280, height: 900 };
const PHONE = { width: 390, height: 844 };
let skills: string[];
let taps = 0;

async function tap(target: Locator) {
  taps++;
  await target.click();
}
async function shoot(page: Page, name: string) {
  for (const [size, at] of [["1280", DESKTOP], ["390", PHONE]] as const) {
    await page.setViewportSize(at);
    await page.screenshot({ path: path.join(SHOTS, `${name}-${size}.png`), fullPage: true });
  }
  await page.setViewportSize(DESKTOP);
}

test.beforeAll(async () => {
  mkdirSync(SHOTS, { recursive: true });
  ({ skills } = await curriculumRows(sql));
});
test.afterAll(async () => {
  await gate(sql, "closed");
  await clearOffers(sql);
  await sql`delete from activity_skill where activity_code like 'ACT-K2-M113-%'`;
  await sql`delete from activity where code like 'ACT-K2-M113-%'`;
  await sql.end();
});
test.beforeEach(async ({ page }) => {
  await gate(sql, "reviewer");
  await page.setViewportSize(DESKTOP);
});

const ADDRESSES = ["/curriculum/browse", "/curriculum/fill", "/curriculum/fill/walk", `/curriculum/fill/${code(2)}`, "/curriculum/offers"];

test("closed to staff with no preview role while the switch is off: every address is not found", async ({ page }) => {
  await gate(sql, "closed");
  for (const url of ADDRESSES) {
    await page.goto(url);
    await expect(page.getByText("This page could not be found."), url).toBeVisible();
  }
});

test("open to head with the switch off (to look, or to review), and to staff once it is on", async ({ page }) => {
  for (const mode of ["look", "reviewer", "open"] as const) {
    await gate(sql, mode);
    for (const url of ADDRESSES) {
      await page.goto(url);
      await expect(page.getByRole("heading", { level: 1 }), `${mode} ${url}`).toBeVisible();
      await expect(page.getByText("This page could not be found.")).toHaveCount(0);
    }
  }
});

test("the pages sit in the school's shell: its menu, a breadcrumb, a strip of counts, a tab bar on a phone", async ({ page }) => {
  await page.goto("/curriculum/fill");
  const side = page.locator('[data-educator-nav="side"]');
  await expect(side.locator("[data-nav=browse], [data-nav=fill], [data-nav=offers]")).toHaveCount(3);
  await expect(side.locator('[data-nav="fill-walk"]')).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Where you are" })).toContainText("What is filled");
  await expect(page.locator("[data-summary] a").first()).toBeVisible();
  await page.setViewportSize(PHONE);
  await expect(page.locator('[data-educator-nav="tabs"] [data-tab]')).toHaveCount(3);
  await expect(side).toBeHidden();
  await page.setViewportSize(DESKTOP);
});

test("the browser counts what is filled per section, with a bar and a state", async ({ page }) => {
  await page.goto("/curriculum/browse");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Curriculum browser");
  for (const [section, state] of [[RED, "red"], [AMBER, "amber"], [GREEN, "green"]] as const) {
    const card = page.locator(`[data-section="${section}"]`);
    await expect(card).toHaveAttribute("data-state", state);
    await expect(card.locator("[role=progressbar]")).toHaveAttribute("aria-valuenow", String(Math.round((100 * FILLED[section]) / (9 * TOTAL[section]))));
    await expect(card.locator("[data-total]")).toHaveText(String(TOTAL[section]));
  }
  const red = page.locator(`[data-section="${RED}"]`);
  await expect(red.locator('[data-slot="objective"]')).toHaveText("3 of 13");
  await expect(red.locator('[data-slot="materials"]')).toHaveText("3 of 13");
  await expect(red.locator('[data-slot="steps"]')).toHaveText("2 of 13");
  await expect(red.locator('[data-slot="level_0"]')).toHaveText("2 of 13");
  await expect(red.locator('[data-slot="skills"]')).toHaveText("2 of 13");
  await shoot(page, "browse");
});

test("a section lists ten rows a page, is searchable, and a row opens its activity", async ({ page }) => {
  await page.goto(`/curriculum/browse?section=${encodeURIComponent(RED)}`);
  await expect(page.locator("[data-row]")).toHaveCount(10);
  await page.getByRole("link", { name: /Later/ }).click();
  await expect(page.locator("[data-row]")).toHaveCount(3);
  await page.goto(`/curriculum/browse?section=${encodeURIComponent(RED)}&q=activity 13`);
  await expect(page.locator("[data-row]")).toHaveCount(1);
  await page.goto(`/curriculum/browse?q=${code(2)}`);
  await page.locator(`[data-row="${code(2)}"] a`).first().click();
  await expect(page).toHaveURL(new RegExp(`/curriculum/fill/${code(2)}$`));
  await page.goto(`/curriculum/browse?q=zzz-no-such-activity`);
  await expect(page.getByText("No activity matches that.")).toBeVisible();
});

test("the fill view counts each part by who wrote it, and the four add up to every activity", async ({ page }) => {
  const [{ n: total }] = await sql<{ n: number }[]>`select count(*)::int as n from activity where band = 'K2'`;
  const [{ n: draftedSteps }] = await sql<{ n: number }[]>`
    select count(*)::int as n from activity_part_source s join activity a on a.tenant_id = s.tenant_id and a.code = s.activity_code
    where a.band = 'K2' and s.part = 'steps' and s.source = 'drafted'`;
  await page.goto("/curriculum/fill");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What is filled, and by whom");
  const row = page.locator('[data-part="steps"]');
  // a column of nothing but zeros is not drawn (rule 4), so a missing cell is a zero
  const cell = async (label: string) => ((await row.locator(`td[data-label="${label}"]`).count()) ? Number(await row.locator(`td[data-label="${label}"]`).innerText()) : 0);
  const counts = [await cell("The school's"), await cell("Drafted, check me"), await cell("Kept by a person"), await cell("Empty")];
  expect(counts.reduce((a, b) => a + b, 0)).toBe(total);
  expect(counts[1]).toBe(draftedSteps);
  await expect(page.locator('[data-part="level_1"] td[data-label="Drafted, check me"]')).toHaveText("1");
  await shoot(page, "fill");
});

test("a person walks the drafted parts one by one: edit, keep, send back — five taps", async ({ page }) => {
  // the review needs no educator switch: head holds a review role (curriculum.review_roles), the switch is off
  taps = 0;
  await page.goto("/curriculum/fill");
  await tap(page.locator("[data-ux=action]").getByRole("link", { name: /Check the drafted parts/ })); // the page's main action (the menu has one too)
  await expect(page.locator("[data-walk]")).toContainText("1 of 3");
  await expect(page.locator('[data-card="steps"] li')).toHaveCount(STEPS.length); // a short list, not a wall
  await shoot(page, "walk-steps");
  await tap(page.getByRole("link", { name: "Edit" }));
  await page.getByLabel("One step on each line").fill("Lay out the cards\nTouch each card once");
  await tap(page.getByRole("button", { name: "Save" }));
  // the thinking: a keyword highlighted and how to spot it
  await expect(page.locator("[data-walk]")).toContainText("1 of 2");
  await expect(page.locator("[data-card=thinking] mark")).toHaveText("Counts twice");
  await expect(page.locator("[data-card=thinking]")).toContainText("points at the same card two times");
  await tap(page.getByRole("button", { name: "Keep" }));
  await expect(page.locator("[data-card=level_1]")).toBeVisible();
  await tap(page.getByRole("button", { name: "Send back" }));
  await expect(page.getByText("Nothing is waiting for a check.")).toBeVisible();
  expect(taps).toBe(5);
  const rows = await sql<{ part: string; source: string }[]>`select part, source from activity_part_source where activity_code = ${code(2)} and part in ('steps','thinking','level_1')`;
  expect(Object.fromEntries(rows.map((r) => [r.part, r.source]))).toEqual({ steps: "person", thinking: "person" });
  const [a] = await sql<{ steps: string; level_1: string }[]>`select steps, level_1 from activity where code = ${code(2)}`;
  expect(a.steps).toBe("• Lay out the cards\n• Touch each card once");
  expect(a.level_1).toBe("");
  await shoot(page, "walk-empty");
});

test("the offered-skills queue shows the activity, skills, what was linked, the reason; yes links, no closes", async ({ page }) => {
  await offers(sql, skills);
  await page.goto("/curriculum/offers");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Skills offered, waiting for you");
  const cards = page.locator("[data-offer]");
  await expect(cards).toHaveCount(2);
  const first = cards.filter({ hasText: "The nearest examples did not carry it." });
  await expect(first).toContainText(code(3));
  await expect(first).toContainText("Placeholder activity 3");
  await expect(first).toContainText(RED);
  await expect(first.locator("[data-offered]")).toContainText(skills[1]);
  await expect(first.locator("[data-linked]")).toContainText(skills[0]);
  await shoot(page, "offers");
  await first.getByRole("button", { name: "Yes, add it" }).click();
  await expect(cards).toHaveCount(1);
  const linked = await sql<{ skill_code: string; source: string }[]>`select skill_code, source from activity_skill where activity_code = ${code(3)} order by skill_code`;
  expect(linked.find((l) => l.skill_code === skills[1])?.source).toBe("machine");
  await cards.first().getByRole("button", { name: "No" }).click();
  await expect(page.getByText("No skills are waiting for you.")).toBeVisible();
  const after = await sql<{ skill_code: string }[]>`select skill_code from activity_skill where activity_code = ${code(3)}`;
  expect(after.map((r) => r.skill_code)).not.toContain(skills[2]);
  await shoot(page, "offers-empty");
  await clearOffers(sql);
});

test("the staff preview looks and changes nothing: the drafts and offers show, with no Keep, Edit, Send back, Yes or No", async ({ page }) => {
  await curriculumRows(sql); // the walk-through above answered the drafts: they are written again
  await gate(sql, "look");
  await offers(sql, skills);
  await page.goto("/curriculum/fill/walk");
  await expect(page.locator("[data-preview]")).toContainText("Preview");
  await expect(page.locator("[data-card=steps] li")).toHaveCount(STEPS.length);
  await expect(page.getByRole("button", { name: /Keep|Send back/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Edit" })).toHaveCount(0);
  await page.goto("/curriculum/offers");
  await expect(page.locator("[data-offer]")).toHaveCount(2);
  await expect(page.getByRole("button", { name: /Yes|No/ })).toHaveCount(0);
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from activity_part_source where activity_code = ${code(2)} and source = 'drafted'`;
  expect(n).toBe(3); // nothing was kept or sent back
  await clearOffers(sql);
});

test("the pages use the tokens and Lucide only: no colour written in, no other icon set", async () => {
  const root = path.resolve(__dirname, "..");
  const files = [
    ...readdirSync(path.join(root, "app/(app)/curriculum"), { recursive: true, encoding: "utf8" }).filter((f) => /\.(tsx?|css)$/.test(f)).map((f) => path.join(root, "app/(app)/curriculum", f)),
    path.join(root, "lib/curriculum-screens.ts"),
  ];
  expect(files.length).toBeGreaterThan(4);
  for (const f of files) {
    const text = readFileSync(f, "utf8");
    expect(text, f).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/);
    expect(text, f).not.toMatch(/from "(react-icons|@heroicons|@phosphor)/);
  }
});
