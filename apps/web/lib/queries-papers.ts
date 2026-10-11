import { sql } from "./db";

// Papers (goals/u9-papers.yaml): every paper, made to signed off, in one list. Nimish, 2026-09-30: "one list of papers
// with the right filtration and all, and a good view". Where each answer stands is the engine's (item_result, and the
// same rule as `answer_standing`); this only counts it per paper.

export const STAGES = ["made", "printed", "scanned", "checked", "signed off"] as const;
export type Stage = (typeof STAGES)[number];

/** Each stage said as the work it waits for (goals/ui2-assessments.yaml); the stored names stay the filter's values. */
export const STAGE_WORDS: Record<Stage, string> = {
  made: "to approve",
  printed: "with the children",
  scanned: "to check",
  checked: "to sign off",
  "signed off": "done",
};

/** A paper's kind in the school's words; `earlier` is a paper sat before our QR sheets, which has no kind. */
export const KIND_WORDS: Record<string, string> = {
  practice: "Class practice",
  assessment: "Class assessment",
  focus: "Home assessment",
  custom: "Chosen paper",
  earlier: "Earlier paper",
};

/** `topic`: papers on a taught topic's skills; `set`: one assessment's copies (`AssessmentRow.set`). */
export type PaperFilter = { class?: string; child?: string; kind?: string; week?: string; stage?: string; topic?: string; set?: string };

export type PaperListRow = {
  id: string;
  qr: string;
  kind: string;
  /** Its skill and level, or a whole paper's title. */
  title: string;
  section: string | null;
  /** The grade the paper is for: its child's, or its worksheet's. */
  band: string | null;
  child_id: string | null;
  child: string | null;
  week: string | null;
  stage: Stage;
  /** Answers the reader could not settle, waiting for a person. */
  waiting: number;
  right: number;
  scored: number;
};

const LIMIT = 300;

/** The papers themselves, each with its stage and counts, before any filter. Void papers are left out. A function, not
 *  a constant: `sql` is touched only when data is asked for (lib/db.ts), never when the page is imported to build. */
const papersCte = () => sql`
  papers as (
    select si.id, si.qr_code as qr, coalesce(si.kind, 'earlier') as kind, si.child_id,
           coalesce(si.section, ch.section) as section, coalesce(ch.band, t.band) as band, coalesce(si.week, t.week) as week,
           coalesce(t.key ->> 'date', si.created_at::date::text) as day, si.created_at,
           coalesce(ss.name || coalesce(' · ' || t.difficulty, ''), t.key ->> 'title', drawn.title, t.code, t.batch_id,
                    si.qr_code) as title,
           case when not a.read then case when si.print_status = 'new' then 'made' else 'printed' end
                when a.n = 0 or a.waiting > 0 then 'scanned'
                when a.candidate > 0 then 'checked'
                else 'signed off' end as stage,
           a.waiting, a.right, a.scored,
           -- one assessment (goals/ui5-assessments-readable.yaml): a kind of paper given to a class in a week on one
           -- skill set (each child a worksheet of its own, the same skill) or on one worksheet; a class's home
           -- assessments and chosen papers for a week are one assessment, each child's drawn for them
           case when coalesce(si.kind, 'earlier') in ('focus', 'custom') then null
                else coalesce(t.skill_set_code, t.id::text) end as set_key,
           coalesce(ss.name, t.key ->> 'title', t.code, t.batch_id, si.qr_code) as set_name,
           -- the topics its questions are on: its skill set's, or each of its questions' own
           array(select distinct s.topic_code from skill_set s
                 where s.tenant_id = t.tenant_id and s.topic_code is not null
                   and (s.code = t.skill_set_code
                        or s.code in (select i.skill_set_code from item i where i.id = any(t.item_ids)))) as topics
    from sheet_instance si
    join sheet_template t on t.id = si.sheet_template_id
    left join child ch on ch.id = si.child_id
    left join skill_set ss on ss.tenant_id = t.tenant_id and ss.code = t.skill_set_code
    -- a paper drawn for one child (a home assessment, a paper an educator chose) names no skill set of its own: its
    -- title is its questions' skill sets and levels, in the order they stand on the page
    left join lateral (
      select string_agg(x.name || ' · ' || x.difficulty, ' + ' order by x.first) as title
      from (select s.name, i.difficulty, min(o.n) as first
            from unnest(t.item_ids) with ordinality o(id, n)
            join item i on i.id = o.id
            join skill_set s on s.tenant_id = i.tenant_id and s.code = i.skill_set_code
            group by s.name, i.difficulty) x
    ) drawn on ss.name is null
    cross join lateral (
      select exists (select 1 from capture k where k.sheet_instance_id = si.id and k.superseded_by is null) as read,
             count(r.id)::int as n,
             count(*) filter (where r.status in ('unreadable', 'needs_teacher'))::int as waiting,
             count(*) filter (where r.state = 'candidate')::int as candidate,
             count(*) filter (where r.status = 'correct')::int as right,
             count(*) filter (where r.status in ('correct', 'wrong', 'blank'))::int as scored
      from capture k join item_result r on r.capture_id = k.id
      where k.sheet_instance_id = si.id and k.superseded_by is null
    ) a
    where si.print_status <> 'void'
  )`;

/** Every filter but the stage: the stage counts are counted across stages. */
const narrowed = (f: PaperFilter) => sql`
  (${f.class ?? null}::text is null or section = ${f.class ?? null})
  and (${f.child ?? null}::uuid is null or child_id = ${f.child ?? null}::uuid)
  and (${f.kind ?? null}::text is null or kind = ${f.kind ?? null})
  and (${f.week ?? null}::text is null or week = ${f.week ?? null})
  and (${f.topic ?? null}::text is null or ${f.topic ?? null} = any(topics))
  and (${f.set ?? null}::text is null or set_key = ${f.set ?? null})`;

/** The papers a filter leaves, newest first (at most 300), with each child's name read once, through pii.read_child,
 *  which logs who asked. */
export async function paperList(f: PaperFilter, actor: string): Promise<{ rows: PaperListRow[]; more: boolean }> {
  const stage = f.stage && (STAGES as readonly string[]).includes(f.stage) ? f.stage : null;
  const rows = await sql<(PaperListRow & { name: string | null })[]>`
    with ${papersCte()},
    shown as (
      select * from papers where ${narrowed(f)} and (${stage}::text is null or stage = ${stage})
      order by day desc nulls last, created_at desc, section, qr
      limit ${LIMIT + 1}
    ),
    names as (
      select c.id, n.first_name from child c, lateral pii.read_child(c.id, ${actor}) n
      where c.id in (select child_id from shown where child_id is not null)
    )
    select s.id, s.qr, s.kind, s.title, s.section, s.band, s.child_id, names.first_name as child, s.week, s.stage,
           s.waiting, s.right, s.scored
    from shown s left join names on names.id = s.child_id
    order by s.day desc nulls last, s.created_at desc, s.section, s.qr`;
  return { rows: rows.slice(0, LIMIT), more: rows.length > LIMIT };
}

/** How many papers stand at each stage under the other filters, and every value each filter can take; children's
 *  names read through pii.read_child, which logs who asked. */
export async function paperFilters(
  f: PaperFilter,
  actor: string,
): Promise<{ stages: Record<Stage, number>; options: { classes: string[]; weeks: string[]; children: { id: string; label: string }[] } }> {
  const [counts, classes, weeks, children] = await Promise.all([
    sql<{ stage: Stage; n: number }[]>`
      with ${papersCte()} select stage, count(*)::int as n from papers where ${narrowed(f)} group by stage`,
    sql<{ section: string }[]>`
      select distinct coalesce(si.section, c.section) as section from sheet_instance si
      left join child c on c.id = si.child_id
      where si.print_status <> 'void' and coalesce(si.section, c.section) is not null order by 1`,
    sql<{ week: string }[]>`
      select week from (select distinct coalesce(si.week, t.week) as week from sheet_instance si
                        join sheet_template t on t.id = si.sheet_template_id where si.print_status <> 'void') w
      where week is not null order by week desc`,
    sql<{ id: string; label: string }[]>`
      select c.id, n.first_name || ' · ' || c.section || ' roll ' || c.roll_no as label
      from child c, lateral pii.read_child(c.id, ${actor}) n
      where c.active and exists (select 1 from sheet_instance si where si.child_id = c.id and si.print_status <> 'void')
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
  copies: number;
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
export async function assessmentList(f: PaperFilter): Promise<{ rows: AssessmentRow[]; more: boolean }> {
  const stage = f.stage && (STAGES as readonly string[]).includes(f.stage) ? f.stage : null;
  const rows = await sql<AssessmentRow[]>`
    with ${papersCte()}
    select kind, section, min(band) as band, week, set_key as set, min(set_name) as title, count(*)::int as copies,
           jsonb_build_object('made', count(*) filter (where stage = 'made'),
                              'printed', count(*) filter (where stage = 'printed'),
                              'scanned', count(*) filter (where stage = 'scanned'),
                              'checked', count(*) filter (where stage = 'checked'),
                              'signed off', count(*) filter (where stage = 'signed off')) as by,
           sum(waiting)::int as waiting,
           coalesce(sum("right") filter (where stage in ('checked', 'signed off')), 0)::int as "right",
           coalesce(sum(scored) filter (where stage in ('checked', 'signed off')), 0)::int as scored
    from papers where ${narrowed(f)} and (${stage}::text is null or stage = ${stage})
    group by kind, section, week, set_key
    order by max(day) desc nulls last, max(created_at) desc, section, min(set_name)
    limit ${LIMIT + 1}`;
  return { rows: rows.slice(0, LIMIT), more: rows.length > LIMIT };
}

