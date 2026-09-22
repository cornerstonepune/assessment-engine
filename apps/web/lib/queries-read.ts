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
  roll_no: string;
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
  select si.id, si.child_id, p.first_name, ch.section, ch.roll_no, t.batch_id as paper,
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

// Every read paper of the child this one belongs to, oldest first (the order of the child's page),
// so a person checking one child steps from paper to paper without going back to a list.
export async function sameChildPapers(id: string): Promise<{ id: string }[]> {
  return sql<{ id: string }[]>`
    select si.id from sheet_instance si join sheet_template t on t.id = si.sheet_template_id
    where si.child_id = (select child_id from sheet_instance where id = ${id}::uuid)
      and exists (select 1 from capture c join item_result r on r.capture_id = c.id
                  where c.sheet_instance_id = si.id and c.superseded_by is null)
    order by t.key ->> 'date', si.created_at`;
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
  // What the reader thinks it saw where it would not stand behind a reading, and — ADR 0032 — who said
  // so: the first reader below its floor, or the second reader shown this child's own answers.
  guess: string | null;
  guess_by: string | null;
};

// A wrong or a blank the engine read but may not settle alone (ADR 0029): a reading for a person to
// confirm or correct, never a Right/Wrong judgement — the engine marks it once the reading is a person's.
// Held (ADR 0029) until a person has said what the child wrote. After that the reading is theirs, and an
// answer code still cannot mark (an explanation has no key) waits for their Right or Wrong: keeping it held
// hid those buttons, so typing the child's words again and again never settled it (2026-09-22).
export const held = (a: Pick<CaptureAnswer, "why" | "human_read">) =>
  a.human_read === null && (a.why ?? "").includes("a person checks every");

// Only a person's Right or Wrong settles this one: its reading is known — the reader's, or what a person
// typed — and code cannot mark it.
export const toJudge = (a: Pick<CaptureAnswer, "status" | "answer_state" | "why" | "human_read">) =>
  a.status === "needs_teacher" && (a.human_read !== null || a.answer_state === "written") && !held(a);

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
           nullif(r.raw_read::jsonb ->> 'guess_by', '') as guess_by,
           (r.raw_read::jsonb ->> 'confidence')::numeric as confidence,
           case when jsonb_typeof(r.raw_read::jsonb -> 'box') = 'array'
                then array(select jsonb_array_elements_text(r.raw_read::jsonb -> 'box'))::numeric[] end as box,
           r.status, r.state, r.working_shown, r.misconception_codes,
           k.human_read, k.by as corrected_by,
           nullif(r.raw_read::jsonb ->> 'guess', '') as guess
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

// How the reader is doing, from every check people have made (ADR 0032) — the same numbers as
// `engine read report`: an answer counts once a person typed its reading or signed it off unchanged.
export type ReaderKind = { fmt: string; checked: number; right: number; gave_up: number; window_n: number; window_right: number; trusted: boolean };
export type ReaderReport = { checked: number; stood_behind: number; right: number; gave_up: number; guess_right: number; kinds: ReaderKind[]; window: number; bar: number };

export async function readerReport(): Promise<ReaderReport> {
  const [gate] = await sql<{ bar: number }[]>`select coalesce((select value from threshold where key = 'marking.agreement_gate'), 0.95)::float as bar`;
  const rows = await sql<{ fmt: string; checked: number; stood_behind: number; right: number; gave_up: number; guess_right: number; window_n: number; window_right: number }[]>`
    with latest as (
      select distinct on (rc.item_result_id) rc.item_result_id, rc.human_read, rc.judged
      from read_correction rc order by rc.item_result_id, rc.created_at desc),
    checked as (
      select i.fmt, c.created_at, coalesce(r.raw_read::jsonb ->> 'why', '') as why,
             regexp_replace(lower(coalesce(r.raw_read::jsonb ->> 'child_answer', '')), '[\s,]', '', 'g') as model_read,
             regexp_replace(lower(coalesce(l.human_read, r.raw_read::jsonb ->> 'child_answer', '')), '[\s,]', '', 'g') as human_read,
             regexp_replace(lower(coalesce(r.raw_read::jsonb ->> 'guess', '')), '[\s,]', '', 'g') as guess
      from item_result r join item i on i.id = r.item_id join capture c on c.id = r.capture_id
      left join latest l on l.item_result_id = r.id
      where c.superseded_by is null and l.judged is null and (l.item_result_id is not null or r.state = 'confirmed')),
    scored as (
      select fmt, (why = '' or why like 'read as%') as stood, model_read = human_read as is_right,
             human_read <> '' and guess = human_read as guess_right,
             row_number() over (partition by fmt, (why = '' or why like 'read as%') order by created_at desc) as rn
      from checked)
    select fmt, count(*)::int as checked,
           count(*) filter (where stood)::int as stood_behind,
           count(*) filter (where stood and is_right)::int as right,
           count(*) filter (where not stood)::int as gave_up,
           count(*) filter (where not stood and guess_right)::int as guess_right,
           count(*) filter (where stood and rn <= 50)::int as window_n,
           count(*) filter (where stood and rn <= 50 and is_right)::int as window_right
    from scored group by fmt order by fmt`;
  const sum = (k: keyof (typeof rows)[number]) => rows.reduce((n, r) => n + Number(r[k]), 0);
  return {
    checked: sum("checked"),
    stood_behind: sum("stood_behind"),
    right: sum("right"),
    gave_up: sum("gave_up"),
    guess_right: sum("guess_right"),
    window: 50,
    bar: gate.bar,
    kinds: rows.map((r) => ({ ...r, trusted: r.window_n >= 50 && r.window_right / r.window_n >= gate.bar })),
  };
}

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
           nullif(r.raw_read::jsonb ->> 'guess_by', '') as guess_by,
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
