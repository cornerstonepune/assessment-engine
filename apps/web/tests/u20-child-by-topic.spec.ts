/**
 * U20 — a child's profile by topic (goals/ui4b1-child-by-topic.yaml). Nimish, 2026-10-11: "It should be by topic or
 * something. When we click on it, we need to think about how multiple topics will then have a view of what the entire
 * profile of the child will look like." A child's page opens on every taught topic, a group whose line counts its
 * skills by where they stand; a topic opens to its skills, those that need help first; papers next, the parent report
 * last; and every parent report waiting on a person is one list — never a child with nothing signed off, whom no report
 * can be written for.
 *
 * The class is the test's own (tests/rows.ts). Its children's skill states are set here directly — the graph's own
 * rules are proved by the engine's tests; this is how the page lays them out — and taken away after.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U20-TEST";
let kids: Record<string, string> = {};
// rung, skill, state: Addition & subtraction secure, practising and needing help; Data handling (Grade 1's) needing help
const STATES: [string, string, string, number, number][] = [
  ["R22", "NUM.OPS.01", "secure", 10, 10],
  ["R21", "NUM.OPS.01", "practising", 5, 3],
  ["R24", "NUM.OPS.02", "patterned_error", 6, 2],
  ["R34", "NUM.DATA.01", "emerging", 3, 1],
];

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G2", ["Ishaan", "Mira", "Kabir"]);
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select tenant_id from child where id = ${kids.Ishaan}`;
  await sql`delete from child_skill_state where child_id = ${kids.Ishaan}`;
  for (const [rung, skill, state, n, right] of STATES) {
    await sql`
      insert into child_skill_state (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, last_seen)
      values (${tenant_id}, ${kids.Ishaan}, ${skill}, ${rung}, ${state}, ${n}, ${right}, now())`;
  }
  // Ishaan's report is written and waits for approval; Kabir has an answer signed off and no report yet; none of Mira's
  // answers is signed off, so she has nothing to report. Kabir's answer is made once: evidence is append-only.
  await sql`delete from parent_note where child_id in (${kids.Ishaan}, ${kids.Mira}, ${kids.Kabir})`;
  await sql`
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel, observed_at, confirmed_by)
    select ${tenant_id}, ${kids.Kabir}, 'NUM.OPS.01', 'R21', true, '{}', 'item', now(), 'e2e'
    where not exists (select 1 from evidence_event where child_id = ${kids.Kabir} and confirmed_by is not null)`;
  const body = {
    facts: { grade: "Grade 2", from: "2026-10-01", to: "2026-10-10", answers: 24, can_do: [], nearly: [], improving: [], working_on: [], next: null },
    draft: { summary: "[child] has worked on addition and subtraction.", can_do: [], working_on: [], at_home: [] },
  };
  await sql`insert into parent_note (tenant_id, child_id, week, body) values (${tenant_id}, ${kids.Ishaan}, '2026-W41', ${JSON.stringify(body)})`;
  // Mira's one answer waits for a person: her page is a page (goals/ux4-class-and-child.yaml), with nothing signed off
  const [w] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where source = 'library' and retired_at is null and band = 'G2'
    order by code limit 1`;
  await aReadPaper(sql, { qr: "U20-MIRA", child: kids.Mira, template: w.id, items: w.item_ids.slice(0, 1), reads: [{ status: "unreadable" }] });
});
test.afterAll(async () => {
  await sql`delete from child_skill_state where child_id = ${kids.Ishaan}`;
  await sql`delete from parent_note where child_id in (${kids.Ishaan}, ${kids.Mira}, ${kids.Kabir})`;
  await sql.end();
});

test("a child's page opens on their profile topic by topic", async ({ page }) => {
  await page.goto(`/growth/${kids.Ishaan}`);
  // each topic is a group whose line counts its skills by where they stand: the profile, said once
  // (goals/ux4-class-and-child.yaml)
  const shown = page.getByRole("region", { name: "What their answers show" });
  const line = (code: string) => shown.locator(`details[data-topic="${code}"] > summary`);
  // the rest of the grade's addition and subtraction taught in the class (reasoning's among them, Grade 2's since
  // ADR 0085) is counted as not assessed yet, not drawn as a wall of grey
  const [{ notYet }] = await sql<{ notYet: number }[]>`
    select count(*)::int - 3 as "notYet" from skill_set s
    where s.topic_code = 'ADDSUB' and s.grade = 'G2'
      and skill_taught_in(s.tenant_id, s.code, (select section from child where id = ${kids.Ishaan}))`;
  await expect(line("ADDSUB")).toContainText(`Addition & subtraction`);
  await expect(line("ADDSUB")).toContainText(`1 needs help · 1 practising · 1 secure · ${notYet} not assessed yet`);
  await expect(line("DATA")).toContainText(/^\W*Data handling\s*1 needs help\b/);
  // a topic not switched on is no part of a child's profile
  await expect(shown).not.toContainText("Multiplication in columns");
});

test("a topic opens to its skills, the ones that need help first", async ({ page }) => {
  await page.goto(`/growth/${kids.Ishaan}`);
  // a topic with a skill that needs help is open already: its skills show (the page streams in hidden, then is shown)
  await expect(page.locator('details[data-topic="ADDSUB"]')).toHaveAttribute("open", "");
  const list = page.getByRole("list", { name: "Addition & subtraction" });
  await expect(list).toBeVisible();
  const skills = list.locator(":scope > li");
  expect(await skills.evaluateAll((els) => els.map((e) => e.getAttribute("data-rag")))).toEqual(["red", "amber", "green"]);
});

test("every parent report waiting on a person is one list, and a child's page ends on theirs", async ({ page }) => {
  // a child's page ends on the parent report, its state in words
  await page.goto(`/growth/${kids.Ishaan}`);
  // the page streams in after its frame (each part read on its own), so the order is read once it is all there
  await expect(page.getByRole("region", { name: "Parent report" })).toBeVisible();
  const regions = await page.getByRole("main").getByRole("region").evaluateAll((els) => els.map((e) => e.getAttribute("aria-label")));
  expect(regions.at(-1)).toBe("Parent report");
  await expect(page.getByRole("region", { name: "Parent report" })).toContainText("Written, waiting for a person to approve it");
  await page.goto(`/growth/${kids.Kabir}`);
  await expect(page.getByRole("region", { name: "Parent report" })).toContainText("Not written yet");
  await expect(page.getByRole("region", { name: "Parent report" }).getByRole("link", { name: "Write it →" })).toBeVisible();
  // nothing signed off is nothing to write from: the engine writes no report from nothing, so no one is asked to
  await page.goto(`/growth/${kids.Mira}`);
  await expect(page.getByRole("region", { name: "Parent report" })).toContainText("Nothing to report yet");
  await expect(page.getByRole("region", { name: "Parent report" }).getByRole("link")).toHaveCount(0);

  // one list: written and waiting before not yet written, each opening the report; a child with nothing to report
  // is not on it
  await page.goto("/growth/reports");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Parent reports");
  const rows = page.getByRole("table", { name: "Parent reports not up to date" }).locator("tbody tr");
  const ours = rows.filter({ hasText: SECTION });
  await expect(ours).toHaveText([/Ishaan.*to approve/, /Kabir.*to write/]);
  await ours.first().getByRole("link", { name: "Ishaan" }).click();
  await expect(page).toHaveURL(new RegExp(`/growth/${kids.Ishaan}/parent$`));

  // Today's line for the reports opens the list
  await page.goto("/today");
  await expect(page.getByRole("region", { name: "Parent reports to approve" }).getByRole("link", { name: /Approve them|Open the list/ })).toHaveAttribute("href", "/growth/reports");
});
