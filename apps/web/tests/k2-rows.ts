// The K2 voice notes' placeholder rows (task M1-04), for the specs that open the K2 screens: a K2 class of the test's own
// ("M104"), 22 children known by Sr. No. alone (first name "Placeholder"), two activities numbered 904 and 907, and the
// signed-in tester on the staff list with a grant for that class. Written as the owner, once; a second run finds them.
import type { Sql } from "postgres";
import { TEST_STAFF } from "./global-setup";

export const SECTION = "M104";
export const ROLLS = Array.from({ length: 22 }, (_, i) => String(i + 1));
export type K2 = { klass: string; staff: string };

export async function k2Class(sql: Sql, section: string = SECTION): Promise<K2> {
  const [{ id: t }] = await sql<{ id: string }[]>`select id from tenant order by created_at limit 1`;
  const [{ id: campus }] = await sql<{ id: string }[]>`select id from campus where tenant_id = ${t} limit 1`;
  const [{ id: year }] = await sql<{ id: string }[]>`
    insert into academic_year (tenant_id, label, starts_on, ends_on) values (${t}, '2031-32', '2026-01-01', '2032-03-31')
    on conflict (tenant_id, label) do update set label = excluded.label returning id`;
  const [{ id: klass }] = await sql<{ id: string }[]>`
    insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section) values (${t}, ${campus}, ${year}, 'K2', ${section})
    on conflict (tenant_id, campus_id, academic_year_id, grade_code, section) do update set section = excluded.section returning id`;
  const [had] = await sql<{ staff_id: string }[]>`select staff_id from pii.staff where email = ${TEST_STAFF.email}`;
  const staff = had?.staff_id ?? (await sql<{ id: string }[]>`insert into staff (tenant_id, campus_id) values (${t}, ${campus}) returning id`)[0].id;
  if (!had) await sql`insert into pii.staff (tenant_id, staff_id, name, email) values (${t}, ${staff}, 'Placeholder Educator', ${TEST_STAFF.email})`;
  await sql`
    insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by)
    select ${t}, ${staff}, 'class_teacher', ${klass}, current_date - 1, 'm1-04 test'
    where not exists (select 1 from staff_role_grant where staff_id = ${staff} and school_class_id = ${klass})`;
  for (const roll of ROLLS) {
    const [on] = await sql`select 1 from enrolment where class_id = ${klass} and roll_no = ${roll} and to_date is null`;
    if (on) continue;
    // the child row may outlive its enrolment (another spec, or a copy that kept children and not enrolments): reuse it
    const [had] = await sql<{ id: string }[]>`select id from child where tenant_id = ${t} and section = ${section} and roll_no = ${roll}`;
    const child = had?.id ?? (await sql<{ id: string }[]>`insert into child (tenant_id, roll_no, section, band) values (${t}, ${roll}, ${section}, 'K2') returning id`)[0].id;
    if (!had) await sql`insert into pii.child (tenant_id, child_id, first_name) values (${t}, ${child}, 'Placeholder')`;
    await sql`insert into enrolment (tenant_id, child_id, class_id, roll_no, from_date, recorded_by) values (${t}, ${child}, ${klass}, ${roll}, '2026-01-01', 'm1-04 test')`;
  }
  const skills = await sql<{ code: string }[]>`select code from registry_skill where tenant_id = ${t} order by code limit 2`;
  // the K2 team's sheet leaves some activities without a number (321 of 871 on live): found by name, never lost
  for (const [no, name] of [["904", "Placeholder sorting activity"], ["907", "Placeholder counting activity"], ["", "Placeholder unnumbered activity"]]) {
    const code = `ACT-K2-M104-${no || "NONE"}`;
    await sql`insert into activity (tenant_id, code, band, strand, name, sheet_no) values (${t}, ${code}, 'K2', 'Maths', ${name}, ${no}) on conflict (tenant_id, code) do nothing`;
    for (const s of skills) await sql`insert into activity_skill (tenant_id, activity_code, skill_code) values (${t}, ${code}, ${s.code}) on conflict do nothing`;
  }
  return { klass, staff };
}

/** A note as the engine leaves it once read: drafted, its words typed, from the tester. */
export async function aK2Note(sql: Sql, k: K2, transcript: string, status = "drafted"): Promise<string> {
  const [{ id }] = await sql<{ id: string }[]>`
    insert into pii.educator_note (tenant_id, staff_id, class_id, audio_key, transcript, status)
    select tenant_id, ${k.staff}, id, ${`voice/2026/${crypto.randomUUID()}.webm`}, ${transcript}, ${status} from school_class where id = ${k.klass}
    returning id::text`;
  return id;
}

/** The two switches: the screens, and recording on top of them (D-065). Recording follows the screens unless said. */
export async function voiceSwitch(sql: Sql, on: boolean, recording = on) {
  await sql`update config set value = ${on ? sql`'true'::jsonb` : sql`'false'::jsonb`} where key = 'voice.screens_enabled'`;
  await sql`delete from config where key = 'voice.recording_enabled'`;
  await sql`insert into config (tenant_id, key, value, description)
    select id, 'voice.recording_enabled', ${recording ? sql`'true'::jsonb` : sql`'false'::jsonb`}, 'm1-04 test' from tenant`;
}

/** Every note the tester left waiting, left unconfirmed (as the 48-hour rule leaves them), so a test reads only its own. */
export const noNotesWaiting = (sql: Sql, k: K2) => sql`update pii.educator_note set status = 'left_unconfirmed' where staff_id = ${k.staff} and status in ('received', 'drafted')`;
