/**
 * U66 — Levels to review (goals/cal_levels_to_review.yaml). Nimish, 26 Oct 2026: "If 8 out of 10 people in the class are
 * able to solve the advanced level for that particular grade or school, then that's not actually advanced. We'll need some
 * section which gives us an understanding that certain things need to be upgraded, like a step." His decisions: the system
 * only suggests, the threshold is 80 percent, the minimum is 8 children.
 *
 * Classes of the test's own, in a grade no school class is in (G10), named afresh each run: evidence is append-only, so a
 * run's rows are kept, and a class of an earlier run is never counted into this one's.
 */
import { expect, test, type Browser } from "@playwright/test";
import { createHmac } from "node:crypto";
import postgres from "postgres";
import { aClass } from "./rows";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const RUN = Date.now().toString(36).toUpperCase();
const BIG = `CALA-${RUN}`; // 10 children: 8 secure at Advance, 2 half right
const SMALL = `CALB-${RUN}`; // 5 children, all secure at Advance: under the minimum
const OTHER = `CALC-${RUN}`; // 8 secure at Advance, a class the educator below does not teach
const GRADE = "G10";
const LEVEL = "Advance";
let skill: { code: string; name: string; rung: string };
let tenant: string;
let registry: string;

type Mark = "right" | "wrong";
const SECURE: Mark[][] = [["right", "right"], ["right", "right"]]; // two papers, four right: the graph's "secure"
const HALF: Mark[][] = [["right", "wrong"], ["right", "wrong"]];

/** A class of children, each with the papers given: a capture and a signed-off answer per mark, as the graph reads them. */
async function seed(section: string, kids: Mark[][][]) {
  const names = kids.map((_, i) => `Kid${i + 1}`);
  const ids = await aClass(sql, section, GRADE, names);
  for (const [i, papers] of kids.entries()) {
    const child = ids[names[i]];
    for (const marks of papers) {
      const tag = `${RUN}${Math.random().toString(16).slice(2, 8)}`.toUpperCase();
      const [tpl] = await sql<{ id: string }[]>`
        insert into sheet_template (tenant_id, band, child_id, week, key, batch_id)
        values (${tenant}, ${GRADE}, ${child}, ${"CAL-" + tag}, ${sql.json({ code: tag })}, ${tag}) returning id`;
      const [inst] = await sql<{ id: string }[]>`
        insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
        values (${tenant}, ${"CS" + tag.slice(-6)}, ${tpl.id}, ${child}, 'returned') returning id`;
      const [cap] = await sql<{ id: string }[]>`
        insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (${tenant}, 'cal.pdf', 1, ${inst.id}, 'processed') returning id`;
      for (const [n, mark] of marks.entries()) {
        const [item] = await sql<{ id: string }[]>`
          insert into item (tenant_id, item_key, template, rung_code, skill_codes, skill_set_code, difficulty, signal, fmt, spec, responses)
          values (${tenant}, ${`cal/${tag}/${n}`}, 'cal', ${skill.rung}, ${sql.array([registry])}, ${skill.code}, ${LEVEL}, 'Procedural', 'column',
                  ${sql.json({ op: "-", a: 62, b: 27, page: 1 })}, ${sql.json([{ rid: "a", answer: 35 }])}) returning id`;
        const [res] = await sql<{ id: string }[]>`
          insert into item_result (tenant_id, capture_id, item_id, rid, status, state, confirmed_by, confirmed_at)
          values (${tenant}, ${cap.id}, ${item.id}, 'a', ${mark === "right" ? "correct" : "wrong"}, 'confirmed', 'cal@cornerstone.test', now()) returning id`;
        await sql`
          insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, item_result_id, observed_at, confirmed_by)
          values (${tenant}, ${child}, ${registry}, ${skill.rung}, ${mark === "right"}, 'item', ${res.id}, now(), 'cal@cornerstone.test')`;
      }
    }
  }
}

test.beforeAll(async () => {
  [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  [{ code: registry }] = await sql<{ code: string }[]>`select code from registry_skill where code = 'NUM.OPS.01' limit 1`;
  [skill] = await sql<{ code: string; name: string; rung: string }[]>`
    select s.code, s.name, s.rung_code as rung from skill s join skill_level l on l.tenant_id = s.tenant_id and l.skill_code = s.code
    where l.difficulty = ${LEVEL} order by s.code limit 1`;
  await seed(BIG, [...Array(8).fill(SECURE), ...Array(2).fill(HALF)]);
  await seed(SMALL, Array(5).fill(SECURE));
  await seed(OTHER, Array(8).fill(SECURE));
});
test.afterAll(async () => {
  await sql.end();
});

const EDUCATOR = { email: `cal-educator-${RUN.toLowerCase()}@cornerstone.test`, name: "Cal Educator", role: "educator", classes: [BIG], subjects: ["NUM"] };
async function asEducator(browser: Browser) {
  await sql`
    update config set value = value || ${sql.json([EDUCATOR])}
    where key = 'app.staff' and not value @> ${sql.json([{ email: EDUCATOR.email }])}`;
  const body = `${Buffer.from(EDUCATOR.email).toString("base64url")}.${Date.now() + 3_600_000}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  const context = await browser.newContext({ baseURL: "http://localhost:3100", viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: "cs_staff", value: `${body}.${mac}`, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" }]);
  return { context, page: await context.newPage() };
}

const ofClass = (section: string) => `/skill-sets/levels?view=class&class=${section}`;

test("the page lists a suggestion in words, with its counts, and links to the skill", async ({ page }) => {
  await page.goto(ofClass(BIG));
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Levels to review");
  const row = page.locator("tr", { hasText: "Most children (8 of 10)" });
  await expect(row).toContainText(`are secure at ${LEVEL} in ${skill.name}. Consider making it harder or adding a harder level.`);
  await expect(row.getByRole("link", { name: skill.name })).toHaveAttribute("href", `/skill-sets/${skill.code}`);
  await expect(row.getByRole("link", { name: "Open the skill" })).toHaveAttribute("href", `/skill-sets/${skill.code}/edit`);
  // under the minimum: the count in words, and no suggestion
  await page.goto(ofClass(SMALL));
  await expect(page.locator("main")).toContainText("not enough children yet (5 of 8)");
  await expect(page.locator("main")).not.toContainText("Consider making it harder");
  // a grade is counted across its classes, on its own: the same figures, said for the grade
  await page.goto(`/skill-sets/levels?view=grade&grade=${GRADE}`);
  await expect(page.locator("main")).toContainText(`are secure at ${LEVEL} in ${skill.name}`);
});

test("a skill's levels fold under the topic and the skill, and the page is on the shared blocks", async ({ page }) => {
  await page.goto(ofClass(BIG));
  const topic = page.locator("details[data-topic]").first();
  await expect(topic, "a topic folds").toBeVisible();
  await expect(topic.locator("details[data-skill]").first(), "a skill folds inside it").toBeVisible();
  await expect(page.locator("[data-filterbar]"), "filters live in the page").toBeVisible();
  await expect(page.locator("[data-ux=action]")).toBeVisible();
  await expect(page.locator("[data-ux=next]")).toBeVisible();
  expect(await page.locator("main table:not(.grid)").count(), "no hand-built table").toBe(0);
  await expect(page.locator(".data-table table").first()).toBeVisible();
  // page load under a second, with this database's rows
  const t0 = Date.now();
  const res = await page.goto(ofClass(BIG));
  expect(res?.status()).toBeLessThan(400);
  expect(Date.now() - t0, "the page answers in under a second").toBeLessThan(1000);
});

test("I've looked at this hides the suggestion for that grade and only adds a row", async ({ page }) => {
  const before = async () => ({
    levels: (await sql`select md5(string_agg(x::text, '|' order by x::text)) as m from skill_level x`)[0].m,
    blob: (await sql`select md5(string_agg(difficulty::text, '|' order by code)) as m from skill`)[0].m,
    reviews: Number((await sql`select count(*) as n from calibration_review where scope_value = ${BIG}`)[0].n),
  });
  const was = await before();
  await page.goto(ofClass(BIG));
  const row = page.locator("tr", { hasText: "Most children (8 of 10)" });
  await row.getByRole("button", { name: "I've looked at this" }).click();
  await expect(page.locator("main")).not.toContainText("Consider making it harder");
  await expect(page.locator("tr", { hasText: `looked at` }).first()).toBeVisible();
  const now = await before();
  expect(now.reviews, "one row added").toBe(was.reviews + 1);
  expect(now.levels, "no level changed").toBe(was.levels);
  expect(now.blob, "no skill's levels changed").toBe(was.blob);
  // the row is only ever added to: the database refuses a change
  await expect(sql`update calibration_review set reviewed_by = 'x' where scope_value = ${BIG}`).rejects.toThrow(/append-only/);
});

test("an educator sees only the classes in their own scope", async ({ browser }) => {
  const { context, page } = await asEducator(browser);
  await page.goto("/skill-sets/levels");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Levels to review");
  await expect(page.locator("main")).toContainText(BIG);
  await expect(page.locator("main")).not.toContainText(OTHER);
  await expect(page.locator("main")).not.toContainText(SMALL);
  // a class that is not theirs, asked for by hand, shows nothing of it
  await page.goto(ofClass(OTHER));
  await expect(page.locator("main")).not.toContainText(OTHER);
  await expect(page.locator("main")).not.toContainText("8 of 8");
  // and the grade's own figures, which count classes they do not teach, are not shown to them
  await page.goto(`/skill-sets/levels?view=grade&grade=${GRADE}`);
  await expect(page.locator("main")).not.toContainText(`Grade 10`);
  await context.close();
});
