/**
 * S43 — the page across every class (goals/s7-across-classes.yaml). Slice S7 of the scope Nimish locked on 2026-10-22:
 * "the coordinator's page across classes: each class and subject's stage, overdue checks, papers missing over 3 days,
 * children struggling in two or more subjects".
 *
 * A Grade 3 class of the test's own (made once and kept: evidence is append-only), and each run its own papers, their
 * codes new each run. A second subject exists only for the last test, made and taken away inside it: today only Maths
 * has children's results, and "two or more subjects" must be seen to count one.
 */
import { randomBytes } from "node:crypto";
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "S43-CLASS";
const RUN = randomBytes(2).toString("hex").toUpperCase();
const code = (n: string) => `CS${RUN}${n}`; // CS + 4 hex of the run + 2 hex of the copy
let kids: Record<string, string> = {};
let tenant = "";
let ws: { id: string; item_ids: string[]; title: string; copy: string };

const paper = (qr: string, child: string | null, printedDaysAgo: number) => sql`
  insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, section, week, kind, print_status,
                              approved_by, approved_at, printed_at, created_at)
  values (${tenant}, ${qr}, ${ws.id}, ${child}, ${SECTION}, to_char(now(), 'IYYY-"W"IW'), 'practice', 'printed', 'e2e',
          now() - make_interval(days => ${printedDaysAgo}), now() - make_interval(days => ${printedDaysAgo}), now())`;

test.beforeAll(async () => {
  kids = await aClass(sql, SECTION, "G3", ["Asha", "Bina", "Chetan"]);
  [{ tenant }] = await sql<{ tenant: string }[]>`select tenant_id as tenant from child where id = ${kids.Asha}`;
  [ws] = await sql<{ id: string; item_ids: string[]; title: string; copy: string }[]>`
    select t.id, t.item_ids, s.name as title, s.name || ' · ' || t.difficulty as copy
    from sheet_template t join skill_set s on s.code = t.skill_set_code
    where t.source = 'library' and t.retired_at is null and t.band = 'G3' and cardinality(t.item_ids) >= 2 order by t.code limit 1`;
  // an earlier run's papers are put away, as a paper made in error is: this run's are the class's newest
  await sql`update sheet_instance set print_status = 'void' where section = ${SECTION} and qr_code not like ${`CS${RUN}%`}`;
  // this run's practice paper: Asha's read 3 days ago with an answer still waiting; Bina's given 5 days ago and not
  // back; Chetan's printed 5 days ago, but he was away
  await paper(code("01"), kids.Asha, 3);
  await paper(code("02"), kids.Bina, 5);
  await paper(code("03"), kids.Chetan, 5);
  const read = await aReadPaper(sql, { qr: code("01"), child: kids.Asha, template: ws.id, items: ws.item_ids.slice(0, 2), reads: [{ status: "correct", read: "1" }, { status: "needs_teacher", read: "7" }] });
  await sql`update capture set created_at = now() - interval '3 days' where id = ${read.capture}`;
  await sql`
    insert into flow_run (tenant_id, flow, trigger, status, finished_at, request)
    values (${tenant}, 'absent', 'e2e: away', 'ok', now(), ${sql.json({ qr: code("03"), away: true, by: "e2e" })})`;
});
test.afterAll(async () => {
  await sql.end();
});

test("each class and subject shows where its newest assessment stands", async ({ page }) => {
  await page.goto("/today");
  await page.getByRole("link", { name: "Across every class" }).first().click();
  await expect(page).toHaveURL(/\/across$/);
  const row = page.getByRole("table", { name: "Each class and subject" }).locator(`tr[data-class="${SECTION}"]`);
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("Maths");
  // named as the Assessments list names it: its skill; each copy says its level
  await expect(row).toContainText(ws.title);
  // its three copies: one read with an answer to check, two with the children
  await expect(row).toContainText("1 to check");
  await expect(row).toContainText("2 with the children");
});

test("answers waiting for a person over 48 hours are overdue", async ({ page }) => {
  await page.goto("/across");
  const line = page.getByRole("region", { name: "Checks overdue" }).locator(`li[data-class="${SECTION}"]`);
  await expect(line).toContainText(/\d+ answers? on \d+ papers? waiting for a person/);
  await expect(page.getByRole("region", { name: "Checks overdue" })).toContainText("waiting over 48 hours");
  // an answer read today is not overdue: the class's count is only what was read over 48 hours ago
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from item_result r join capture k on k.id = r.capture_id and k.superseded_by is null
    join sheet_instance si on si.id = k.sheet_instance_id left join child ch on ch.id = si.child_id
    where r.status in ('unreadable', 'needs_teacher') and coalesce(si.section, ch.section) = ${SECTION}
      and k.created_at < now() - interval '48 hours'`;
  await expect(line).toContainText(`${n} ${n === 1 ? "answer" : "answers"} on`);
});

test("papers given over 3 days ago and not back are listed", async ({ page }) => {
  await page.goto("/across");
  const missing = page.getByRole("table", { name: "Papers not back" });
  const bina = missing.getByRole("row").filter({ hasText: code("02") });
  await expect(bina).toContainText(ws.copy);
  await expect(bina.locator("td.num")).toHaveText("5");
  // Asha's came back; Chetan was away, so his is carried, not missing
  await expect(missing).not.toContainText(code("01"));
  await expect(missing).not.toContainText(code("03"));
});

test("a child who needs help in two subjects is named, and one subject alone is not enough", async ({ page }) => {
  const [maths] = await sql<{ rung: string; skill: string }[]>`
    select ss.rung_code as rung, ss.registry_codes[1] as skill from skill_set ss
    where ss.grade = 'G3' and cardinality(ss.registry_codes) > 0 order by ss.ladder_order, ss.code limit 1`;
  await sql.begin(async (tx) => {
    await tx`insert into subject (tenant_id, code, name, label) values (${tenant}, 'S43SUB', 'Test subject', 'Test subject')`;
    await tx`insert into topic (tenant_id, code, subject_code, name, ord) values (${tenant}, 'S43TOPIC', 'S43SUB', 'Test topic', 99)`;
    // a skill's grade and description are its own (goals/b4-the-rung-folded-in.yaml); its second code names it in evidence
    await tx`
      insert into skill_set (tenant_id, code, rung_code, name, learning_objective, difficulty, topic_code, grade, descriptor)
      values (${tenant}, 'S43.SET', 'S43R', 'A test skill', 'a test', '{}'::jsonb, 'S43TOPIC', 'G3', 'a test skill')`;
  });
  // where each child stands is rebuilt from the evidence any time (ring B): a red state in Maths for both, and in the
  // test subject for Asha alone
  const red = async (child: string, rung: string) => sql`
    insert into child_skill_state (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct)
    values (${tenant}, ${child}, ${maths.skill}, ${rung}, 'emerging', 4, 0)
    on conflict (tenant_id, child_id, skill_code, rung_code) do update set state = 'emerging'`;
  try {
    await red(kids.Asha, maths.rung);
    await red(kids.Asha, "S43R");
    await red(kids.Bina, maths.rung);
    await page.goto("/across");
    const help = page.getByRole("region", { name: "Needing help in two or more subjects" });
    await expect(help.getByRole("listitem").filter({ hasText: "Asha" })).toContainText(`${SECTION} · Roll 1: needs help in Maths and Test subject`);
    await expect(help).not.toContainText("Bina");
    await help.getByRole("link", { name: "Asha" }).click();
    await expect(page).toHaveURL(new RegExp(`/growth/${kids.Asha}$`));
  } finally {
    await sql`delete from child_skill_state where rung_code = 'S43R'`;
    for (const id of [kids.Asha, kids.Bina]) await sql`select rebuild_child_skill_state(${id}::uuid)`;
    await sql`delete from skill_set where code = 'S43.SET'`;
    await sql`delete from topic where code = 'S43TOPIC'`;
    await sql`delete from subject where code = 'S43SUB'`;
  }
});
