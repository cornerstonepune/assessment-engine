import { sql } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";
import type { Difficulty } from "./queries";

// Class papers to approve (goals/ui3-curriculum.yaml, goals/ux5-papers-grouped.yaml): a class's week, each child by name
// with the level they are set and why, the paper they were handed, and every child of the class with no paper and why.
// Names are read through pii.read_child, which logs who asked.

export type WeekRow = {
  prescription_id: string;
  child_id: string;
  roll_no: string;
  first_name: string;
  band: string;
  section: string;
  skill_set_code: string;
  skill_set_name: string;
  difficulty: Difficulty;
  rule_fired: string;
  override_by: string | null;
  override_reason: string | null;
  qr_code: string | null;
  print_status: string | null;
  worksheet: string | null; // the library worksheet it is, when it came from the library
  /** Why the week's assembly could not give this child a paper (w2_print/assemble.py), while they have none. */
  no_paper: string | null;
};

export async function weeks(scope: Scope = EVERY_CLASS): Promise<{ section: string; week: string; kind: string; n: number }[]> {
  return sql`
    select c.section, p.week, p.kind, count(*)::int as n
    from prescription p join child c on c.id = p.child_id
    where ${inScope(scope, sql`c.section`)}
    group by c.section, p.week, p.kind
    order by p.week desc, c.section, p.kind`;
}

export async function weekPlan(section: string, week: string, kind: string, actor: string): Promise<WeekRow[]> {
  return sql<WeekRow[]>`
    select p.id as prescription_id, p.child_id, c.roll_no, n.first_name, c.band, c.section,
           p.skill_set_code, s.name as skill_set_name, p.difficulty, p.rule_fired,
           p.override_by, p.override_reason, p.no_paper,
           si.qr_code, si.print_status, st.code as worksheet
    from prescription p
    join child c on c.id = p.child_id
    cross join lateral pii.read_child(c.id, ${actor}) n
    left join skill s on s.tenant_id = p.tenant_id and s.code = p.skill_set_code
    left join sheet_instance si on si.id = p.sheet_instance_id
    left join sheet_template st on st.id = si.sheet_template_id
    where c.section = ${section} and p.week = ${week} and p.kind = ${kind}
    order by roll_order(c.roll_no), c.roll_no`;
}

/** The class's children on the roll with no plan for this week: `later`, those who joined after it was made. */
export async function unplanned(
  section: string,
  week: string,
  kind: string,
  actor: string,
): Promise<{ child_id: string; roll_no: string; first_name: string; later: boolean }[]> {
  return sql`
    select c.id as child_id, c.roll_no, n.first_name,
           c.created_at > (select min(p.created_at) from prescription p join child k on k.id = p.child_id
                           where k.section = ${section} and p.week = ${week} and p.kind = ${kind}) as later
    from child c cross join lateral pii.read_child(c.id, ${actor}) n
    where c.section = ${section} and c.active
      and not exists (select 1 from prescription p where p.child_id = c.id and p.week = ${week} and p.kind = ${kind})
    order by roll_order(c.roll_no), c.roll_no`;
}

/** The pack's spares: papers with no name on them, for a spoilt page or a child who arrives late. */
export async function spareSheets(
  section: string,
  week: string,
  kind: string,
): Promise<{ qr_code: string; difficulty: string; worksheet: string | null; print_status: string }[]> {
  return sql`
    select si.qr_code, st.difficulty, st.code as worksheet, si.print_status from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id
    where si.child_id is null and si.print_status <> 'void'
      and (si.section = ${section} and si.week = ${week} and si.kind = ${kind}
           or si.section is null and st.week = ${week}
              and st.band in (select distinct band from child where section = ${section}))
    order by st.difficulty, si.qr_code`;
}
