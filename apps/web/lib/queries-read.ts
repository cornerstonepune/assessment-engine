/**
 * W3 — reading papers and putting them in front of a person. Its own module so `queries.ts` stays
 * one screen per workflow, the same boundary `cli_read.py` draws on the engine side.
 *
 * The unit is the SHEET — this child's copy of this paper — not the file it arrived in. A Grade 2
 * sitting is one scanned PDF and a Grade 3 sitting is one photograph per page, and a teacher signs
 * off the paper either way.
 */
import { sql } from "./db";

// ---- the approval queue. One row per paper a child sat, and every answer on it.
//
// The unit is the SHEET — this child's copy of this paper — not the file it arrived in. A Grade 2
// sitting is one scanned PDF and a Grade 3 sitting is one photograph per page, and a teacher signs
// off the paper either way.

export type PaperRow = {
  id: string;
  child_id: string;
  first_name: string;
  section: string;
  paper: string;
  title: string;
  date: string | null;
  pages: number;
  files: number;
  n_results: number;
  n_flagged: number;
  n_candidate: number;
  n_confirmed: number;
  n_corrected: number;
  // The sheet's score: answers marked right, of every answer marked right, wrong or blank.
  n_right: number;
  n_scored: number;
};

const paperRows = (where: ReturnType<typeof sql>, actor: string) => sql<PaperRow[]>`
  select si.id, si.child_id, p.first_name, ch.section, t.batch_id as paper,
         t.key ->> 'title' as title, t.key ->> 'date' as date,
         coalesce(jsonb_array_length(t.key -> 'pages'), 1) as pages,
         (select count(*)::int from capture c
           where c.sheet_instance_id = si.id and c.superseded_by is null) as files,
         (select count(*)::int from item_result r join capture c on c.id = r.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null) as n_results,
         (select count(*)::int from item_result r join capture c on c.id = r.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null
             and r.state = 'candidate' and r.status in ('unreadable', 'needs_teacher')) as n_flagged,
         (select count(*)::int from item_result r join capture c on c.id = r.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null and r.state = 'candidate') as n_candidate,
         (select count(*)::int from item_result r join capture c on c.id = r.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null and r.state = 'confirmed') as n_confirmed,
         (select count(*)::int from read_correction rc join capture c on c.id = rc.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null) as n_corrected,
         (select count(*)::int from item_result r join capture c on c.id = r.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null and r.status = 'correct') as n_right,
         (select count(*)::int from item_result r join capture c on c.id = r.capture_id
           where c.sheet_instance_id = si.id and c.superseded_by is null
             and r.status in ('correct', 'wrong', 'blank')) as n_scored
  from sheet_instance si
  join sheet_template t on t.id = si.sheet_template_id
  join child ch on ch.id = si.child_id, lateral pii.read_child(si.child_id, ${actor}) p
  where ${where}
  order by t.key ->> 'date' desc nulls last, p.first_name`;

// Every paper that has been read. Names come through pii.read_child, which logs who asked
// (rule 6) — a queue of papers is still a list of children.
export async function papersToApprove(actor: string): Promise<PaperRow[]> {
  return paperRows(
    sql`exists (select 1 from capture c where c.sheet_instance_id = si.id and c.superseded_by is null)`,
    actor,
  );
}

export async function paperHeader(id: string, actor: string): Promise<PaperRow | undefined> {
  const rows = await paperRows(sql`si.id = ${id}::uuid`, actor);
  return rows[0];
}

export type CaptureAnswer = {
  id: string;
  capture_id: string;
  slot: string;
  n: number | null;
  page: number;
  question: string;
  kind: string;
  rung_code: string;
  skill_code: string;
  answer: string | null;
  read: string | null;
  answer_state: string | null;
  // Why this answer reached a person, in the reader's own words — "3 numbers in the region for 2
  // answers", "under the confidence floor". A teacher looking at eighteen crops needs to know
  // which of them are her judgement to make and which are the engine admitting it could not see.
  why: string | null;
  confidence: number | null;
  box: number[] | null;
  status: string;
  state: string;
  working_shown: string;
  misconception_codes: string[];
  human_read: string | null;
  corrected_by: string | null;
};

// Every answer on one paper, in the order they sit on the page — which is the order a teacher
// reads them in, with the photograph beside them.
export async function paperAnswers(id: string): Promise<CaptureAnswer[]> {
  return sql<CaptureAnswer[]>`
    select r.id, r.capture_id, split_part(i.item_key, '/', 3) as slot,
           nullif(regexp_replace(split_part(i.item_key, '/', 3), '[^0-9]', '', 'g'), '')::int as n,
           coalesce((i.spec ->> 'page')::int, 1) as page,
           coalesce(i.spec ->> 'question', i.stem) as question,
           coalesce(i.spec ->> 'kind', 'bare') as kind, i.rung_code, i.skill_codes[1] as skill_code,
           coalesce(i.spec ->> 'answer', i.responses -> 0 ->> 'answer') as answer,
           r.raw_read::jsonb ->> 'child_answer' as read,
           r.raw_read::jsonb ->> 'answer_state' as answer_state,
           nullif(r.raw_read::jsonb ->> 'why', '') as why,
           (r.raw_read::jsonb ->> 'confidence')::numeric as confidence,
           case when jsonb_typeof(r.raw_read::jsonb -> 'box') = 'array'
                then array(select jsonb_array_elements_text(r.raw_read::jsonb -> 'box'))::numeric[] end as box,
           r.status, r.state, r.working_shown, r.misconception_codes,
           k.human_read, k.by as corrected_by
    from item_result r
    join capture c on c.id = r.capture_id
    join item i on i.id = r.item_id
    left join lateral (
      select rc.human_read, rc.by from read_correction rc
       where rc.item_result_id = r.id and rc.judged is null order by rc.created_at desc limit 1
    ) k on true
    where c.sheet_instance_id = ${id}::uuid and c.superseded_by is null
    order by page, n, slot`;
}

// ---- the queue: every answer the engine is unsure of, one at a time (goals/s4-validation-queue.yaml).
//
// Waiting means what `engine read waiting` means — a live reading the engine could not settle — so the
// count on the screen is the engine's own. One answer the engine WAS sure of on each paper is mixed in
// as a spot-check: the smallest md5 of its id, so it is the same one every time and needs no row of
// its own; it leaves the queue once a person has looked at it.

export type QueueEntry = { id: string; spot: boolean };

export async function checkQueue(): Promise<QueueEntry[]> {
  return sql<QueueEntry[]>`
    with live as (
      select r.id, r.status, r.state, r.raw_read, r.item_id, c.sheet_instance_id
      from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null
    ),
    spot as (
      select distinct on (l.sheet_instance_id) l.id, l.state
      from live l
      where l.status in ('correct', 'wrong', 'blank') and l.raw_read::jsonb ->> 'answer_state' = 'written'
      order by l.sheet_instance_id, md5(l.id::text)
    ),
    q as (
      select l.id, false as spot from live l where l.status in ('unreadable', 'needs_teacher')
      union all
      select s.id, true from spot s
      where s.state = 'candidate' and not exists (select 1 from read_correction rc where rc.item_result_id = s.id)
    )
    select q.id, q.spot from q
    join live l on l.id = q.id
    join item i on i.id = l.item_id
    join sheet_instance si on si.id = l.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    join child ch on ch.id = si.child_id
    order by t.key ->> 'date' desc nulls last, ch.roll_no, si.id, coalesce((i.spec ->> 'page')::int, 1),
             nullif(regexp_replace(split_part(i.item_key, '/', 3), '[^0-9]', '', 'g'), '')::int, i.item_key`;
}

export type CheckItem = CaptureAnswer & {
  paper_id: string;
  first_name: string;
  paper_title: string | null;
  sat: string | null;
  guess: string | null;
};

// One answer from the queue, with the child's first name — read through pii.read_child, which logs
// who asked (rule 6): one name per answer shown, never the whole queue's.
export async function checkItem(id: string, actor: string): Promise<CheckItem | undefined> {
  const rows = await sql<CheckItem[]>`
    select r.id, r.capture_id, split_part(i.item_key, '/', 3) as slot,
           nullif(regexp_replace(split_part(i.item_key, '/', 3), '[^0-9]', '', 'g'), '')::int as n,
           coalesce((i.spec ->> 'page')::int, 1) as page,
           coalesce(i.spec ->> 'question', i.stem) as question,
           coalesce(i.spec ->> 'kind', 'bare') as kind, i.rung_code, i.skill_codes[1] as skill_code,
           coalesce(i.spec ->> 'answer', i.responses -> 0 ->> 'answer') as answer,
           r.raw_read::jsonb ->> 'child_answer' as read,
           r.raw_read::jsonb ->> 'answer_state' as answer_state,
           nullif(r.raw_read::jsonb ->> 'why', '') as why,
           (r.raw_read::jsonb ->> 'confidence')::numeric as confidence,
           case when jsonb_typeof(r.raw_read::jsonb -> 'box') = 'array'
                then array(select jsonb_array_elements_text(r.raw_read::jsonb -> 'box'))::numeric[] end as box,
           r.status, r.state, r.working_shown, r.misconception_codes,
           k.human_read, k.by as corrected_by,
           si.id as paper_id, p.first_name, t.key ->> 'title' as paper_title, t.key ->> 'date' as sat,
           nullif(r.raw_read::jsonb ->> 'guess', '') as guess
    from item_result r
    join capture c on c.id = r.capture_id
    join item i on i.id = r.item_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id,
    lateral pii.read_child(si.child_id, ${actor}) p
    left join lateral (
      select rc.human_read, rc.by from read_correction rc
       where rc.item_result_id = r.id and rc.judged is null order by rc.created_at desc limit 1
    ) k on true
    where r.id = ${id}::uuid`;
  return rows[0];
}
