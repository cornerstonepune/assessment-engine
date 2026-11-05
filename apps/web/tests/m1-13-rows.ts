// Placeholder rows for the curriculum screens (task M1-13): three sections of the test's own, each activity numbered by
// the test, and the fill each one has. No name of a child or of staff; the signed-in tester is the only member of staff.
// Written as the owner; a second run clears what the first wrote and writes it again.
import type { Sql } from "postgres";
import { TEST_STAFF } from "./global-setup";

export const RED = "M113 Red";
export const AMBER = "M113 Amber";
export const GREEN = "M113 Green";
export const code = (n: number) => `ACT-K2-M113-${String(n).padStart(2, "0")}`;
export const STEPS = ["Sort the cards by colour", "Count the red cards"];
const STEPS_TEXT = STEPS.map((s) => `• ${s}`).join("\n");
export const SLIPS = [{ keyword: "Counts twice", spot: "points at the same card two times" }];
const THINKING_TEXT = ["Counting is touching each thing once", ...SLIPS.map((s) => `• ${s.keyword}: ${s.spot}`)].join("\n");

const FULL = {
  objective: "Counts up to ten", materials: "Cards", steps: STEPS_TEXT, thinking: THINKING_TEXT,
  level_0: "Needs help", level_1: "Counts some", level_2: "Counts to ten", level_3: "Counts to twenty",
};

async function activity(sql: Sql, t: string, n: number, strand: string, parts: Partial<typeof FULL>, skills: string[]) {
  const c = code(n);
  await sql`
    insert into activity (tenant_id, code, band, strand, name, sheet_no, objective, materials, steps, thinking, level_0, level_1, level_2, level_3)
    values (${t}, ${c}, 'K2', ${strand}, ${`Placeholder activity ${n}`}, '', ${parts.objective ?? ""}, ${parts.materials ?? ""}, ${parts.steps ?? ""},
            ${parts.thinking ?? ""}, ${parts.level_0 ?? ""}, ${parts.level_1 ?? ""}, ${parts.level_2 ?? ""}, ${parts.level_3 ?? ""})`;
  for (const s of skills) await sql`insert into activity_skill (tenant_id, activity_code, skill_code) values (${t}, ${c}, ${s}) on conflict do nothing`;
  return c;
}

const mark = (sql: Sql, t: string, c: string, part: string, source: string, check: boolean) =>
  sql`insert into activity_part_source (tenant_id, activity_code, part, source, check_me) values (${t}, ${c}, ${part}, ${source}, ${check})`;

/** What the fixtures hold, for the specs to compare the screens with. */
export const FILLED = { [RED]: 20, [AMBER]: 9, [GREEN]: 18 } as const;
export const TOTAL = { [RED]: 13, [AMBER]: 2, [GREEN]: 2 } as const;

export async function curriculumRows(sql: Sql): Promise<{ skills: string[] }> {
  const [{ id: t }] = await sql<{ id: string }[]>`select id from tenant order by created_at limit 1`;
  const skills = (await sql<{ code: string }[]>`select code from registry_skill where tenant_id = ${t} order by code limit 4`).map((r) => r.code);
  // the engine knows a member of staff by a row of pii.staff: the signed-in tester gets one, as the voice specs do
  const [had] = await sql<{ staff_id: string }[]>`select staff_id from pii.staff where email = ${TEST_STAFF.email}`;
  if (!had) {
    const [{ id: campus }] = await sql<{ id: string }[]>`select id from campus where tenant_id = ${t} limit 1`;
    const [{ id: staff }] = await sql<{ id: string }[]>`insert into staff (tenant_id, campus_id) values (${t}, ${campus}) returning id`;
    await sql`insert into pii.staff (tenant_id, staff_id, name, email) values (${t}, ${staff}, 'Placeholder Educator', ${TEST_STAFF.email})`;
  }
  await sql`delete from activity where tenant_id = ${t} and code like 'ACT-K2-M113-%'`;
  // red: 13 activities, 20 of 117 slots filled — the first full with a skill, the second drafted in three parts, the third a person's objective, the fifth materials only
  await activity(sql, t, 1, RED, FULL, [skills[0]]);
  const a2 = await activity(sql, t, 2, RED, FULL, [skills[0]]);
  await activity(sql, t, 3, RED, { objective: "Counts to five" }, []);
  await activity(sql, t, 4, RED, {}, []);
  await activity(sql, t, 5, RED, { materials: "Beads" }, []);
  for (let n = 6; n <= 13; n++) await activity(sql, t, n, RED, {}, []);
  await sql`update activity set steps_list = ${sql.json(STEPS)}, thinking_doc = ${sql.json({ idea: "Counting is touching each thing once", slips: SLIPS })} where tenant_id = ${t} and code = ${a2}`;
  await mark(sql, t, a2, "steps", "drafted", true);
  await mark(sql, t, a2, "thinking", "drafted", true);
  await mark(sql, t, a2, "level_1", "drafted", false);
  await mark(sql, t, a2, "objective", "school", false);
  await mark(sql, t, code(3), "objective", "person", false);
  // amber: one full, one empty — half. green: two full.
  await activity(sql, t, 14, AMBER, FULL, [skills[0]]);
  await activity(sql, t, 15, AMBER, {}, []);
  await activity(sql, t, 16, GREEN, FULL, [skills[0]]);
  await activity(sql, t, 17, GREEN, FULL, [skills[1]]);
  return { skills };
}

/** Two skills offered for activity 3, which already has one skill linked by the school. */
export async function offers(sql: Sql, skills: string[]): Promise<void> {
  const [{ id: t }] = await sql<{ id: string }[]>`select id from tenant order by created_at limit 1`;
  await sql`delete from activity_skill where tenant_id = ${t} and activity_code = ${code(3)}`;
  await sql`insert into activity_skill (tenant_id, activity_code, skill_code, source) values (${t}, ${code(3)}, ${skills[0]}, 'person')`;
  await clearOffers(sql);
  const run = crypto.randomUUID();
  for (const [skill, also, reason] of [[skills[1], skills[0], "The nearest examples did not carry it."], [skills[2], "", "Counting objects needs it too."]]) {
    await sql`
      insert into curriculum_proposal (tenant_id, run_id, kind, subject_code, proposal, confidence, status, reason, machine)
      values (${t}, ${run}, 'skill_offer', ${code(3)}, ${sql.json({ skills: [skill], with: also ? [also] : [] })}, 0.8, 'needs_person', ${reason}, 'm1-13 test')`;
  }
}

/** The ledger is append-only (it refuses a delete), so a leftover offer is closed the way a person closes one: a
 *  `rejected` row that moves on it. */
export async function clearOffers(sql: Sql): Promise<void> {
  await sql`
    insert into curriculum_proposal (tenant_id, run_id, about, kind, subject_code, status, reason, staff_id)
    select p.tenant_id, p.run_id, p.id, p.kind, p.subject_code, 'rejected', 'm1-13 test clean-up', (select staff_id from pii.staff where email = ${TEST_STAFF.email})
    from curriculum_proposal p
    where p.about is null and p.status = 'needs_person' and p.subject_code like 'ACT-K2-M113-%'
      and not exists (select 1 from curriculum_proposal f where f.about = p.id)`;
}

/** Who the curriculum gate lets in (D-076, and the review rule): "closed" (the educator switch off, the tester holds no
 *  role), "reviewer" (switch off, the tester holds head, a role `curriculum.review_roles` names: looks and changes things),
 *  "look" (switch off, head, but review_roles names another role: the staff preview, who only looks), "open" (switch on).
 *  Put back with `gate(sql, "closed")`, which also puts the review roles back as seeded. */
export async function gate(sql: Sql, mode: "closed" | "reviewer" | "look" | "open") {
  await sql`update config set value = ${mode === "open" ? sql`'true'::jsonb` : sql`'false'::jsonb`} where key = 'educator.timetable_enabled'`;
  await sql`update config set value = ${sql.json(mode === "look" ? ["ops"] : ["head", "coordinator"])} where key = 'curriculum.review_roles'`;
  const [{ staff_id: staff, tenant_id: t }] = await sql<{ staff_id: string; tenant_id: string }[]>`select staff_id, tenant_id from pii.staff where email = ${TEST_STAFF.email}`;
  // a grant is never deleted and an ended one is never reopened (the table refuses both): "closed" ends this test's grants
  // by their date, and the others give the tester a new one unless one is open
  if (mode === "closed" || mode === "open") {
    await sql`update staff_role_grant set valid_to = valid_from where staff_id = ${staff} and granted_by = 'm1-13b test' and valid_to is null`;
    return;
  }
  const [open] = await sql`select 1 from staff_role_grant where staff_id = ${staff} and granted_by = 'm1-13b test' and valid_to is null`;
  if (!open) await sql`insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by) values (${t}, ${staff}, 'head', current_date - 1, 'm1-13b test')`;
}
