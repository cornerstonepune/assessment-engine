import { sql } from "./db";
import { papersCte, STAGES, type Stage } from "./queries-papers";

// The page across every class (goals/s7-across-classes.yaml), slice S7 of the scope Nimish locked on 2026-10-22: "the
// coordinator's page across classes: each class and subject's stage, overdue checks, papers missing over 3 days,
// children struggling in two or more subjects". Every number is counted here from the rows the other pages read: a
// paper's stage is the Assessments list's own (`papersCte`); a child's standing is the Children page's
// (child_skill_state, coloured by child_state); a skill's subject is its topic's. How long is "overdue" and "missing"
// is a row each (threshold `across.*`), never a number here.

/** A class's newest assessment in one subject, and how many of its copies stand at each stage. */
export type ClassStage = { section: string; band: string; subject: string; title: string; week: string | null; by: Partial<Record<Stage, number>> };
export type Overdue = { section: string; band: string; answers: number; papers: number; oldest: string };
export type Missing = { section: string; band: string; roll_no: string | null; qr: string; title: string; since: string; days: number };
export type Struggling = { child_id: string; section: string; band: string; roll_no: string; name: string; subjects: string[] };
export type Across = { stages: ClassStage[]; overdue: Overdue[]; missing: Missing[]; struggling: Struggling[]; days: number; hours: number; subjects: number };

export async function across(actor: string): Promise<Across> {
  const [[limits], stages, overdue, missing, struggling, [{ subjects }]] = await Promise.all([
    sql<{ days: number; hours: number }[]>`
      select (select value from threshold where key = 'across.papers_missing_days')::int as days,
             (select value from threshold where key = 'across.check_overdue_hours')::int as hours`,
    // each class and subject: its newest assessment (by the day its newest copy was made), its copies by stage
    sql<{ section: string; band: string; subject: string; title: string; week: string | null; by: Partial<Record<Stage, number>> }[]>`
      with ${papersCte()},
      placed as (
        select p.*, coalesce(su.label, su.name) as subject
        from papers p cross join lateral unnest(p.topics) tc(code)
        join topic t on t.tenant_id = p.tenant_id and t.code = tc.code
        join subject su on su.tenant_id = t.tenant_id and su.code = t.subject_code
        where p.section is not null and not p.spare and p.stage <> 'replaced'
      ),
      one as (
        select distinct tenant_id, section, class_band, subject, kind, week, set_key, set_name, id, stage, created_at from placed
      ),
      newest as (
        select distinct on (section, subject) section, subject, kind, week, set_key
        from (select section, subject, kind, week, set_key, max(created_at) as at from one group by 1, 2, 3, 4, 5) a
        order by section, subject, at desc
      )
      select o.section, o.class_band as band, o.subject, min(o.set_name) as title, o.week,
             jsonb_object_agg(o.stage, o.n) as by
      from (select one.tenant_id, one.section, one.class_band, one.subject, one.set_name, one.week, one.stage, count(*)::int as n
            from one join newest n using (section, subject, kind)
            where one.week is not distinct from n.week and one.set_key is not distinct from n.set_key
            group by 1, 2, 3, 4, 5, 6, 7) o
      group by o.tenant_id, o.section, o.class_band, o.subject, o.week
      order by grade_ord(o.tenant_id, o.class_band), o.section, o.subject`,
    // answers waiting for a person longer than the threshold since their paper was read
    sql<Overdue[]>`
      select coalesce(si.section, ch.section) as section, class_band(si.tenant_id, coalesce(si.section, ch.section)) as band,
             count(*)::int as answers, count(distinct k.id)::int as papers,
             to_char(min(k.created_at) at time zone 'Asia/Kolkata', 'YYYY-MM-DD') as oldest
      from item_result r join capture k on k.id = r.capture_id and k.superseded_by is null
      join sheet_instance si on si.id = k.sheet_instance_id left join child ch on ch.id = si.child_id
      where r.status in ('unreadable', 'needs_teacher') and coalesce(si.section, ch.section) is not null
        and k.created_at < now() - make_interval(hours => (select value from threshold where key = 'across.check_overdue_hours')::int)
      group by 1, 2 order by min(k.created_at)`,
    // a child's paper given (or printed, where no one said the day) longer ago than the threshold and not back; a child
    // said to be away is carried, not missing (w2_print/given.py)
    sql<Missing[]>`
      with out as (
        select si.qr_code as qr, ch.section, ch.roll_no, si.tenant_id,
               coalesce(ss.name || coalesce(' · ' || t.difficulty, ''), t.key ->> 'title', t.code) as title,
               coalesce((select max((g.request ->> 'on')::date) from flow_run g
                         where g.flow = 'given' and g.request -> 'qrs' ? si.qr_code),
                        coalesce(si.printed_at, si.approved_at)::date) as since
        from sheet_instance si join child ch on ch.id = si.child_id and ch.active
        join sheet_template t on t.id = si.sheet_template_id
        left join skill_set ss on ss.tenant_id = t.tenant_id and ss.code = t.skill_set_code
        where si.print_status in ('printed', 'with_teacher')
          and not exists (select 1 from capture k where k.sheet_instance_id = si.id and k.superseded_by is null)
          and coalesce((select (a.request ->> 'away')::boolean from flow_run a where a.flow = 'absent'
                        and a.request ->> 'qr' = si.qr_code order by a.started_at desc, a.id desc limit 1), false) = false
      )
      select section, class_band(tenant_id, section) as band, roll_no, qr, title, since::text as since,
             (current_date - since)::int as days
      from out where since < current_date - (select value from threshold where key = 'across.papers_missing_days')::int
      order by grade_ord(tenant_id, class_band(tenant_id, section)), section, roll_order(roll_no), roll_no, since`,
    // a child who needs help (a red state with enough answers) in two or more subjects; names read through
    // pii.read_child, which logs who asked
    sql<Struggling[]>`
      with red as (
        select s.child_id, t.subject_code
        from child_skill_state s join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
        join skill_set ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code
        join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
        where cs.enough and cs.colour = 'red'
        group by 1, 2
      ),
      many as (select child_id, array_agg(subject_code order by subject_code) as codes from red group by 1 having count(*) >= 2)
      select c.id as child_id, c.section, class_band(c.tenant_id, c.section) as band, c.roll_no, n.first_name as name,
             array(select coalesce(su.label, su.name) from subject su where su.tenant_id = c.tenant_id and su.code = any(m.codes) order by su.code) as subjects
      from many m join child c on c.id = m.child_id and c.active, lateral pii.read_child(c.id, ${actor}) n
      order by grade_ord(c.tenant_id, class_band(c.tenant_id, c.section)), c.section, roll_order(c.roll_no), c.roll_no`,
    sql<{ subjects: number }[]>`
      select count(distinct t.subject_code)::int as subjects from child_skill_state s
      join skill_set ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code`,
  ]);
  return { stages, overdue, missing, struggling, days: limits.days, hours: limits.hours, subjects };
}

/** Where a class's newest assessment stands, in the Assessments list's words: its least advanced copies first. */
export const stageOrder = STAGES.filter((s) => s !== "replaced");
