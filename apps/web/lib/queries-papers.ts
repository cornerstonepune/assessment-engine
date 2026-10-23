import { sql } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";

// Papers (goals/u9-papers.yaml): every paper, made to signed off, in one list. Nimish, 2026-09-30: "one list of papers
// with the right filtration and all, and a good view". Where each answer stands is the engine's (item_result, and the
// same rule as `answer_standing`); this only counts it per paper.

// `replaced`: a home assessment made again the same week, never read — the newest is the week's
// (goals/home-assessment-remake.yaml); one that comes back is read, and stands where its answers stand
export const STAGES = ["made", "printed", "scanned", "checked", "signed off", "replaced"] as const;
export type Stage = (typeof STAGES)[number];

/** Each stage said as the work it waits for (goals/ui2-assessments.yaml); the stored names stay the filter's values. */
export const STAGE_WORDS: Record<Stage, string> = {
  made: "to approve",
  printed: "with the children",
  scanned: "to check",
  checked: "to sign off",
  "signed off": "done",
  replaced: "replaced by a newer one",
};

/** A paper as a person names it, as the list below names it: the skill and level it tests, else the school's own title;
 *  a home assessment, each area at its own level, by its kind; a worksheet's code only where nothing else names it
 *  (goals/ux8b-papers-named.yaml). `t` is the query's alias for the paper's `sheet_template`. */
export const paperName = (t: string) => sql`
  coalesce((select s.name || ' · ' || ${sql(t)}.difficulty from skill s
             where s.tenant_id = ${sql(t)}.tenant_id and s.code = ${sql(t)}.skill_set_code),
           ${sql(t)}.key ->> 'title',
           case when ${sql(t)}.source = 'focus' then 'Home assessment' end,
           ${sql(t)}.code)`;

/** A paper's kind in the school's words; `earlier` is a paper sat before our QR sheets, which has no kind. */
export const KIND_WORDS: Record<string, string> = {
  practice: "Class practice",
  assessment: "Class assessment",
  focus: "Home assessment",
  custom: "Chosen paper",
  earlier: "Earlier paper",
};

/** `topic`: papers on a taught topic's skills; `set`: one assessment's copies (`AssessmentRow.set`). */
export type PaperFilter = {
  class?: string;
  child?: string;
  kind?: string;
  week?: string;
  stage?: string;
  topic?: string;
  set?: string;
  /** A subject's code (`subject.code`): the papers whose skills are in it. */
  subject?: string;
  /** Words in the assessment's name. */
  q?: string;
};

export type PaperListRow = {
  id: string;
  qr: string;
  kind: string;
  /** Its skill and level, or a whole paper's title. */
  title: string;
  section: string | null;
  /** The grade the paper is for: its child's; a spare's, its class's; a paper given to no class, its worksheet's. */
  band: string | null;
  child_id: string | null;
  child: string | null;
  roll_no: string | null;
  /** How hard the copy is: its worksheet's level; none for a paper drawn from several. */
  level: string | null;
  /** The assessment it is a copy of (`AssessmentRow.set`). */
  set: string | null;
  /** A class's spare copy, not yet written on: it goes with its class's pack and waits for no one of its own. */
  spare: boolean;
  week: string | null;
  stage: Stage;
  /** Answers the reader could not settle, waiting for a person. */
  waiting: number;
  right: number;
  scored: number;
  /** Of `scored`, the answers left blank. */
  blank: number;
  /** A copy never handed back beside another copy of the same child's, which is read: said apart, not a second child. */
  extra: boolean;
};

const LIMIT = 300;

/** The papers themselves, each with its stage and counts, before any filter. Void papers are left out. A function, not
 *  a constant: `sql` is touched only when data is asked for (lib/db.ts), never when the page is imported to build. */
export const papersCte = () => sql`
  papers_raw as (
    select si.id, si.tenant_id, si.qr_code as qr, coalesce(si.kind, 'earlier') as kind, si.child_id, ch.roll_no, t.difficulty as level,
           -- a child's copy is at the child's grade, a spare at its class's (class_band, the one rule), and only a paper
           -- given to no class at its worksheet's (goals/ux2-one-count-one-thing.yaml)
           coalesce(si.section, ch.section) as section, coalesce(ch.band, cls.band, t.band) as band, cls.band as class_band,
           coalesce(si.week, t.week) as week,
           si.child_id is null and si.section is not null and not a.read as spare,
           coalesce(t.key ->> 'date', si.created_at::date::text) as day, si.created_at,
           coalesce(ss.name || coalesce(' · ' || t.difficulty, ''), t.key ->> 'title', drawn.title, t.code, t.batch_id,
                    si.qr_code) as title,
           case when not a.read and si.kind = 'focus' and exists (
                  select 1 from sheet_instance n where n.kind = 'focus' and n.child_id = si.child_id
                    and n.week = si.week and n.created_at > si.created_at and n.print_status <> 'void') then 'replaced'
                when not a.read then case when si.print_status = 'new' then 'made' else 'printed' end
                when a.n = 0 or a.waiting > 0 then 'scanned'
                when a.candidate > 0 then 'checked'
                else 'signed off' end as stage,
           a.waiting, a.right, a.scored, a.blank,
           -- one assessment (goals/ui5-assessments-readable.yaml): a kind of paper given to a class in a week on one
           -- skill set (each child a worksheet of its own, the same skill) or on one worksheet; a class's home
           -- assessments and chosen papers for a week are one assessment, each child's drawn for them
           -- a class paper made in the maker is drawn for each child on a worksheet of its own: it is one assessment by
           -- its skills and levels, which every child's copy names (goals/ux5-papers-grouped.yaml) — it was a row a child
           case when coalesce(si.kind, 'earlier') in ('focus', 'custom') then null
                when t.skill_set_code is null and si.key ? 'areas' then 'areas:' || (si.key -> 'areas')::text
                else coalesce(t.skill_set_code, t.id::text) end as set_key,
           coalesce(ss.name, t.key ->> 'title', drawn.title, t.code, t.batch_id, si.qr_code) as set_name,
           -- the subject of its questions' topics (one of them, by code, where a paper spans two)
           (select min(tp.subject_code) from skill s join topic tp on tp.tenant_id = s.tenant_id and tp.code = s.topic_code
             where s.tenant_id = t.tenant_id
               and (s.code = t.skill_set_code or s.code in (select i.skill_set_code from item i where i.id = any(t.item_ids)))) as subject,
           -- the topics its questions are on: its skill set's, or each of its questions' own
           array(select distinct s.topic_code from skill s
                 where s.tenant_id = t.tenant_id and s.topic_code is not null
                   and (s.code = t.skill_set_code
                        or s.code in (select i.skill_set_code from item i where i.id = any(t.item_ids)))) as topics
    from sheet_instance si
    join sheet_template t on t.id = si.sheet_template_id
    left join child ch on ch.id = si.child_id
    left join (select k.tenant_id, k.section, class_band(k.tenant_id, k.section) as band
               from (select distinct tenant_id, section from child where active) k) cls
      on cls.tenant_id = si.tenant_id and cls.section = coalesce(si.section, ch.section)
    left join skill ss on ss.tenant_id = t.tenant_id and ss.code = t.skill_set_code
    -- a paper drawn for one child (a home assessment, a paper an educator chose) names no skill set of its own: its
    -- title is its questions' skill sets and levels, in the order they stand on the page
    left join lateral (
      select string_agg(x.name || ' · ' || x.difficulty, ' + ' order by x.first) as title
      from (select s.name, i.difficulty, min(o.n) as first
            from unnest(t.item_ids) with ordinality o(id, n)
            join item i on i.id = o.id
            join skill s on s.tenant_id = i.tenant_id and s.code = i.skill_set_code
            group by s.name, i.difficulty) x
    ) drawn on ss.name is null
    cross join lateral (
      select exists (select 1 from capture k where k.sheet_instance_id = si.id and k.superseded_by is null) as read,
             count(r.id)::int as n,
             count(*) filter (where r.status in ('unreadable', 'needs_teacher'))::int as waiting,
             count(*) filter (where r.state = 'candidate')::int as candidate,
             count(*) filter (where r.status = 'correct')::int as right,
             count(*) filter (where r.status in ('correct', 'wrong', 'blank'))::int as scored,
             count(*) filter (where r.status = 'blank')::int as blank
      from capture k join item_result r on r.capture_id = k.id
      where k.sheet_instance_id = si.id and k.superseded_by is null
    ) a
    where si.print_status <> 'void'
  ),
  -- an extra copy: a child's copy of an assessment never handed back, beside another copy of the same assessment that is
  -- read. A second batch of the same class's papers (the pack made twice) gives every child a second sheet; the read
  -- one is the child's copy and this is said apart, never counted as a second child (goals/dup_answers_listed_twice.yaml)
  papers as (
    select r.*, r.set_key is not null and r.child_id is not null and r.stage in ('made', 'printed')
           and exists (select 1 from papers_raw o
                       where o.id <> r.id and o.child_id = r.child_id and o.kind = r.kind and o.section is not distinct from r.section
                         and o.week is not distinct from r.week and o.set_key = r.set_key
                         and o.stage in ('scanned', 'checked', 'signed off')) as extra
    from papers_raw r
  )`;

/** Every filter but the stage: the stage counts are counted across stages. Only the classes a person sees. */
const narrowed = (f: PaperFilter, scope: Scope) => sql`
  ${inScope(scope, sql`section`)}
  and (${f.class ?? null}::text is null or section = ${f.class ?? null})
  and (${f.child ?? null}::uuid is null or child_id = ${f.child ?? null}::uuid)
  and (${f.kind ?? null}::text is null or kind = ${f.kind ?? null})
  and (${f.week ?? null}::text is null or week = ${f.week ?? null})
  and (${f.topic ?? null}::text is null or ${f.topic ?? null} = any(topics))
  and (${f.set ?? null}::text is null or set_key = ${f.set ?? null})
  and (${f.subject ?? null}::text is null or subject = ${f.subject ?? null})
  and (${f.q ?? null}::text is null or position(lower(${f.q ?? ""}) in lower(set_name)) > 0)`;

/** The papers a filter leaves (at most 300) — newest first, or an assessment's copies in roll order, its spares last
 *  (goals/ux5-papers-grouped.yaml) — with each child's name read once, through pii.read_child, which logs who asked. */
export async function paperList(
  f: PaperFilter,
  actor: string,
  scope: Scope = EVERY_CLASS,
  order: "newest" | "roll" = "newest",
): Promise<{ rows: PaperListRow[]; more: boolean }> {
  const stage = f.stage && (STAGES as readonly string[]).includes(f.stage) ? f.stage : null;
  const by = order === "roll" ? sql`roll_no is null, roll_order(roll_no), roll_no, qr` : sql`day desc nulls last, created_at desc, section, qr`;
  const rows = await sql<(PaperListRow & { name: string | null })[]>`
    with ${papersCte()},
    shown as (
      select * from papers where ${narrowed(f, scope)} and (${stage}::text is null or stage = ${stage})
      order by ${by}
      limit ${LIMIT + 1}
    ),
    names as (
      select c.id, n.first_name from child c, lateral pii.read_child(c.id, ${actor}) n
      where c.id in (select child_id from shown where child_id is not null)
    )
    select s.id, s.qr, s.kind, s.title, s.section, s.band, s.child_id, names.first_name as child, s.roll_no, s.level,
           s.set_key as set, s.spare, s.extra, s.week, s.stage, s.waiting, s.right, s.scored, s.blank
    from shown s left join names on names.id = s.child_id
    order by ${order === "roll" ? sql`s.roll_no is null, roll_order(s.roll_no), s.roll_no, s.qr` : sql`s.day desc nulls last, s.created_at desc, s.section, s.qr`}`;
  return { rows: rows.slice(0, LIMIT), more: rows.length > LIMIT };
}

/** How many papers stand at each stage under the other filters, and every value each filter can take; children's
 *  names read through pii.read_child, which logs who asked. */
export async function paperFilters(
  f: PaperFilter,
  actor: string,
  scope: Scope = EVERY_CLASS,
): Promise<{ stages: Record<Stage, number>; options: { classes: string[]; weeks: string[]; children: { id: string; label: string }[] } }> {
  const [counts, classes, weeks, children] = await Promise.all([
    sql<{ stage: Stage; n: number }[]>`
      with ${papersCte()} select stage, count(*)::int as n from papers where ${narrowed(f, scope)} and not spare and not extra group by stage`,
    sql<{ section: string }[]>`
      select distinct coalesce(si.section, c.section) as section from sheet_instance si
      left join child c on c.id = si.child_id
      where si.print_status <> 'void' and coalesce(si.section, c.section) is not null
        and ${inScope(scope, sql`coalesce(si.section, c.section)`)} order by 1`,
    sql<{ week: string }[]>`
      select week from (select distinct coalesce(si.week, t.week) as week from sheet_instance si
                        join sheet_template t on t.id = si.sheet_template_id where si.print_status <> 'void') w
      where week is not null order by week desc`,
    sql<{ id: string; label: string }[]>`
      select c.id, n.first_name || ' · ' || c.section || ' roll ' || c.roll_no as label
      from child c, lateral pii.read_child(c.id, ${actor}) n
      where c.active and ${inScope(scope, sql`c.section`)}
        and exists (select 1 from sheet_instance si where si.child_id = c.id and si.print_status <> 'void')
      order by c.section, roll_order(c.roll_no), c.roll_no`,
  ]);
  const stages = Object.fromEntries(STAGES.map((s) => [s, 0])) as Record<Stage, number>;
  for (const c of counts) stages[c.stage] = c.n;
  return { stages, options: { classes: classes.map((c) => c.section), weeks: weeks.map((w) => w.week), children } };
}

export type AssessmentRow = {
  kind: string;
  section: string | null;
  band: string | null;
  week: string | null;
  /** Its skill set or worksheet, which opens its copies; none for a class's home assessments, which the class, week and
   *  kind already name. */
  set: string | null;
  title: string;
  /** The code of its subject (`subject.code`), where its questions' topics name one. */
  subject: string | null;
  /** Its children's copies' paper codes, for the day it was given (`givenOn`). */
  qrs: string[];
  /** Its children's copies; its spares, not yet written on, apart: they go with the pack. */
  copies: number;
  spares: number;
  /** Its children's second copies, never handed back, beside a copy that is read. */
  extras: number;
  /** Its copies at each stage. */
  by: Record<Stage, number>;
  waiting: number;
  right: number;
  scored: number;
};

/** The assessments a filter leaves (goals/ui5-assessments-readable.yaml), newest first, at most 300: each a kind of
 *  paper given to a class in a week on one skill set or worksheet, or a class's home assessments for a week, with its
 *  copies counted by stage — a stage chosen keeps the copies at that stage — the answers waiting for a person, and its
 *  score across the copies that are checked. */
export async function assessmentList(f: PaperFilter, scope: Scope = EVERY_CLASS): Promise<{ rows: AssessmentRow[]; more: boolean }> {
  const stage = f.stage && (STAGES as readonly string[]).includes(f.stage) ? f.stage : null;
  const rows = await sql<AssessmentRow[]>`
    with ${papersCte()}
    -- the lowest grade of its copies, by the grades' order (grade_ord), never as text
    select kind, section, coalesce((array_agg(class_band order by grade_ord(tenant_id, class_band)) filter (where class_band is not null))[1],
                                   (array_agg(band order by grade_ord(tenant_id, band)))[1]) as band, week, set_key as set, min(set_name) as title,
           min(subject) as subject, array_agg(qr) filter (where not spare and not extra) as qrs,
           count(*) filter (where not spare and not extra)::int as copies, count(*) filter (where spare)::int as spares,
           count(*) filter (where extra)::int as extras,
           jsonb_build_object('made', count(*) filter (where stage = 'made' and not spare and not extra),
                              'printed', count(*) filter (where stage = 'printed' and not spare and not extra),
                              'scanned', count(*) filter (where stage = 'scanned'),
                              'checked', count(*) filter (where stage = 'checked'),
                              'signed off', count(*) filter (where stage = 'signed off'),
                              'replaced', count(*) filter (where stage = 'replaced')) as by,
           sum(waiting)::int as waiting,
           coalesce(sum("right") filter (where stage in ('checked', 'signed off')), 0)::int as "right",
           coalesce(sum(scored) filter (where stage in ('checked', 'signed off')), 0)::int as scored
    from papers where ${narrowed(f, scope)} and (${stage}::text is null or stage = ${stage})
    group by kind, section, week, set_key
    order by max(day) desc nulls last, max(created_at) desc, section, min(set_name)
    limit ${LIMIT + 1}`;
  return { rows: rows.slice(0, LIMIT), more: rows.length > LIMIT };
}


/** The assessment a paper is one of, and how many of its children's papers are not yet signed off: when none are, the
 *  card's Results are complete (goals/chk_whose_paper.yaml). A spare, or a paper replaced by a newer one, is not waited for. */
export async function assessmentOf(id: string) {
  const [row] = await sql<{ kind: string; section: string | null; week: string | null; set: string | null; left: number }[]>`
    with ${papersCte()}
    select p.kind, p.section, p.week, p.set_key as set,
           (select count(*)::int from papers q
             where q.kind = p.kind and q.section is not distinct from p.section and q.week is not distinct from p.week
               and q.set_key is not distinct from p.set_key and q.child_id is not null
               and q.stage not in ('signed off', 'replaced')) as left
    from papers p where p.id = ${id}::uuid`;
  return row;
}

/** The day each assessment was given, as the educator said it on the card (`flow_run`, flow "given"): the newest day over
 *  its copies, by the assessment's `qrs`. An assessment never given has none. */
export async function givenOn(rows: readonly { qrs: string[] }[]): Promise<Map<string, string>> {
  const qrs = [...new Set(rows.flatMap((r) => r.qrs ?? []))];
  if (!qrs.length) return new Map();
  const found = await sql<{ qr: string; on: string }[]>`
    select q.value as qr, max(r.request ->> 'on') as on
    from flow_run r cross join lateral jsonb_array_elements_text(r.request -> 'qrs') q(value)
    where r.flow = 'given' and jsonb_typeof(r.request -> 'qrs') = 'array' and q.value = any(${qrs})
    group by q.value`;
  return new Map(found.map((f) => [f.qr, f.on]));
}
