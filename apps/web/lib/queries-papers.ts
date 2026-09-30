import { sql } from "./db";

// Papers (goals/u9-papers.yaml): every paper, made to signed off, in one list. Nimish, 2026-09-30: "one list of papers
// with the right filtration and all, and a good view". Where each answer stands is the engine's (item_result, and the
// same rule as `answer_standing`); this only counts it per paper.

export const STAGES = ["made", "printed", "scanned", "checked", "signed off"] as const;
export type Stage = (typeof STAGES)[number];

/** A paper's kind in the school's words; `earlier` is a paper sat before our QR sheets, which has no kind. */
export const KIND_WORDS: Record<string, string> = {
  practice: "Class practice",
  assessment: "Class assessment",
  focus: "Home assessment",
  custom: "Chosen paper",
  earlier: "Earlier paper",
};

export type PaperFilter = { class?: string; child?: string; kind?: string; week?: string; stage?: string };

export type PaperListRow = {
  id: string;
  qr: string;
  kind: string;
  /** Its skill and level, or a whole paper's title. */
  title: string;
  section: string | null;
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
           coalesce(si.section, ch.section) as section, coalesce(si.week, t.week) as week,
           coalesce(t.key ->> 'date', si.created_at::date::text) as day, si.created_at,
           coalesce(ss.name || coalesce(' · ' || t.difficulty, ''), t.key ->> 'title', drawn.title, t.code, t.batch_id,
                    si.qr_code) as title,
           case when not a.read then case when si.print_status = 'new' then 'made' else 'printed' end
                when a.n = 0 or a.waiting > 0 then 'scanned'
                when a.candidate > 0 then 'checked'
                else 'signed off' end as stage,
           a.waiting, a.right, a.scored
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
  and (${f.week ?? null}::text is null or week = ${f.week ?? null})`;

/** The papers a filter leaves, newest first (at most 300), with each child's name read once, through pii.read_child,
 *  which logs who asked; how many papers stand at each stage under the other filters; and every value each filter
 *  can take. */
export async function paperList(
  f: PaperFilter,
  actor: string,
): Promise<{
  rows: PaperListRow[];
  more: boolean;
  stages: Record<Stage, number>;
  options: { classes: string[]; weeks: string[]; children: { id: string; label: string }[] };
}> {
  const stage = f.stage && (STAGES as readonly string[]).includes(f.stage) ? f.stage : null;
  const [rows, counts, classes, weeks, children] = await Promise.all([
    sql<(PaperListRow & { name: string | null })[]>`
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
      select s.id, s.qr, s.kind, s.title, s.section, s.child_id, names.first_name as child, s.week, s.stage,
             s.waiting, s.right, s.scored
      from shown s left join names on names.id = s.child_id
      order by s.day desc nulls last, s.created_at desc, s.section, s.qr`,
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
      order by c.section, coalesce(nullif(regexp_replace(c.roll_no, '\\D', '', 'g'), '')::int, 9999), c.roll_no`,
  ]);
  const stages = Object.fromEntries(STAGES.map((s) => [s, 0])) as Record<Stage, number>;
  for (const c of counts) stages[c.stage] = c.n;
  return {
    rows: rows.slice(0, LIMIT),
    more: rows.length > LIMIT,
    stages,
    options: { classes: classes.map((c) => c.section), weeks: weeks.map((w) => w.week), children },
  };
}
