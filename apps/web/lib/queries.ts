import { sql } from "./db";

export const DIFFICULTIES = ["Easy", "Medium", "Hard", "Advance"] as const;
export type Difficulty = (typeof DIFFICULTIES)[number];

export type Band = { words: string; check: Record<string, unknown> };

export type SkillSet = {
  code: string;
  rung_code: string;
  name: string;
  learning_objective: string;
  philosophy: string[];
  formats: string[];
  misconception_codes: string[];
  difficulty: Record<Difficulty, Band>;
  status: "draft" | "ratified";
  ratified_by: string | null;
  updated_at: string;
  band: string;
  descriptor: string;
  skill_codes: string[];
  counts: Partial<Record<Difficulty, number>>;
};

export async function skillSets(): Promise<SkillSet[]> {
  return sql<SkillSet[]>`
    select s.code, s.rung_code, s.name, s.learning_objective, s.philosophy, s.formats,
           s.misconception_codes, s.difficulty, s.status, s.ratified_by, s.updated_at,
           r.band, r.descriptor, r.skill_codes,
           coalesce((select json_object_agg(d.difficulty, d.n)
                     from (select difficulty, count(*)::int as n from item
                           where item.skill_set_code = s.code and item.status = 'active'
                           group by difficulty) d), '{}'::json) as counts
    from skill_set s
    join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    order by r.ladder_order nulls last, s.code`;
}

export async function skillSet(code: string): Promise<SkillSet | undefined> {
  const rows = await skillSets();
  return rows.find((s) => s.code === code);
}

export type Skill = { code: string; name: string; description: string; rungs: string[] };

export async function numSkills(): Promise<Skill[]> {
  return sql<Skill[]>`
    select k.code, k.name, k.description,
           coalesce(array_agg(r.code order by r.ladder_order) filter (where r.code is not null), '{}') as rungs
    from skill k
    left join rung r on r.tenant_id = k.tenant_id and k.code = any(r.skill_codes)
    where k.domain = 'NUM'
    group by k.code, k.name, k.description
    order by k.code`;
}

export type Misconception = { code: string; op: string; name: string; description: string };

export async function misconceptionsFor(op: string): Promise<Misconception[]> {
  return sql<Misconception[]>`
    select distinct on (code) code, op, name, description from misconception
    where op = ${op} or op = 'both' order by code`;
}

export async function misconceptionNames(): Promise<Record<string, string>> {
  const rows = await sql<{ code: string; name: string }[]>`select distinct on (code) code, name from misconception order by code`;
  return Object.fromEntries(rows.map((r) => [r.code, r.name]));
}

export type ItemRow = {
  id: string;
  item_key: string;
  fmt: string;
  stem: string;
  spec: { a?: number; b?: number; op?: string; text?: string; layout?: string; missing?: string };
  responses: { rid: string; answer: string; misconceptions: Record<string, number> }[];
  tags: Record<string, string | number | number[]>;
  status: string;
  times_used: number;
  skill_set_code: string | null;
  difficulty: string | null;
  created_at: string;
};

export type ItemFilter = { set?: string; difficulty?: string; fmt?: string; status?: string };

export async function items(f: ItemFilter, limit = 200): Promise<ItemRow[]> {
  return sql<ItemRow[]>`
    select id, item_key, fmt, stem, spec, responses, tags, status, times_used, skill_set_code, difficulty, created_at
    from item
    where source = 'generated'
      ${f.set ? sql`and skill_set_code = ${f.set}` : sql``}
      ${f.difficulty ? sql`and difficulty = ${f.difficulty}` : sql``}
      ${f.fmt ? sql`and fmt = ${f.fmt}` : sql``}
      ${f.status ? sql`and status = ${f.status}` : sql`and status = 'active'`}
    order by created_at desc, item_key
    limit ${limit}`;
}

export async function itemFacets(): Promise<{ fmts: string[]; sets: string[] }> {
  const [fmts, sets] = await Promise.all([
    sql<{ fmt: string }[]>`select distinct fmt from item where source = 'generated' order by fmt`,
    sql<{ code: string }[]>`select code from skill_set order by code`,
  ]);
  return { fmts: fmts.map((r) => r.fmt), sets: sets.map((r) => r.code) };
}

// Honest empty states read the real tables so a screen can say what exists, even when that is nothing.
export async function tableCounts(): Promise<Record<string, number>> {
  const rows = await sql<{ t: string; n: number }[]>`
    select 'prescription' as t, count(*)::int as n from prescription
    union all select 'sheet_instance', count(*)::int from sheet_instance
    union all select 'capture', count(*)::int from capture
    union all select 'item_result', count(*)::int from item_result
    union all select 'evidence_event', count(*)::int from evidence_event
    union all select 'child', count(*)::int from child
    union all select 'child_skill_state', count(*)::int from child_skill_state
    union all select 'home_sheet', count(*)::int from home_sheet
    union all select 'parent_note', count(*)::int from parent_note`;
  return Object.fromEntries(rows.map((r) => [r.t, r.n]));
}

export type WeekRow = {
  prescription_id: string;
  child_id: string;
  roll_no: string;
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
  questions: number | null;
};

export const RULE_WORDS: Record<string, string> = {
  band_default: "Not enough of their own work yet, so this is the starting level for their grade.",
  from_state: "From what this child's last papers showed.",
  override: "A teacher set this by hand.",
};

export async function weeks(): Promise<{ section: string; week: string; kind: string; n: number }[]> {
  return sql`
    select c.section, p.week, p.kind, count(*)::int as n
    from prescription p join child c on c.id = p.child_id
    group by c.section, p.week, p.kind
    order by p.week desc, c.section, p.kind`;
}

export async function weekPlan(section: string, week: string, kind: string): Promise<WeekRow[]> {
  return sql<WeekRow[]>`
    select p.id as prescription_id, p.child_id, c.roll_no, c.band, c.section,
           p.skill_set_code, s.name as skill_set_name, p.difficulty, p.rule_fired,
           p.override_by, p.override_reason,
           si.qr_code, si.print_status, array_length(st.item_ids, 1) as questions
    from prescription p
    join child c on c.id = p.child_id
    left join skill_set s on s.tenant_id = p.tenant_id and s.code = p.skill_set_code
    left join sheet_instance si on si.id = p.sheet_instance_id
    left join sheet_template st on st.id = si.sheet_template_id
    where c.section = ${section} and p.week = ${week} and p.kind = ${kind}
    order by coalesce(nullif(regexp_replace(c.roll_no, '\\D', '', 'g'), '')::int, 9999), c.roll_no`;
}

export async function spareSheets(section: string, week: string): Promise<{ qr_code: string; difficulty: string }[]> {
  return sql`
    select si.qr_code, st.difficulty from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id
    where si.child_id is null and st.week = ${week}
      and st.band in (select distinct band from child where section = ${section})
    order by st.difficulty, si.qr_code`;
}

export type Staff = { email: string; name: string; role: string; password?: string };

export async function staffList(): Promise<Staff[]> {
  const row = await sql<{ value: Staff[] }[]>`select value from config where key = 'app.staff'`;
  return row[0]?.value ?? [];
}

// ---- Child Growth: what confirmed evidence says about one child, and what still waits for a person.

export const STATE_WORDS: Record<string, { words: string; tone: "neem" | "bamboo" | "terracotta" | "monsoon" }> = {
  not_enough_yet: { words: "not enough yet", tone: "monsoon" },
  patterned_error: { words: "repeating mistake", tone: "terracotta" },
  emerging: { words: "emerging", tone: "bamboo" },
  practising: { words: "practising", tone: "bamboo" },
  secure: { words: "secure", tone: "neem" },
  stretch_ready: { words: "ready to move up", tone: "neem" },
};

export type ChildRow = {
  id: string;
  roll_no: string;
  section: string;
  band: string;
  first_name: string;
  n_events: number;
  n_pending: number;
  n_papers: number;
};

// Every name read goes through pii.read_child, which logs who asked (rule 6).
export async function childrenOnRoll(actor: string): Promise<ChildRow[]> {
  return sql<ChildRow[]>`
    select c.id, c.roll_no, c.section, c.band, p.first_name,
           (select count(*)::int from evidence_event e where e.child_id = c.id and e.confirmed_by is not null) as n_events,
           (select count(*)::int from item_result r join capture k on k.id = r.capture_id
              join sheet_instance si on si.id = k.sheet_instance_id
             where si.child_id = c.id and r.state = 'candidate') as n_pending,
           (select count(*)::int from capture k join sheet_instance si on si.id = k.sheet_instance_id
             where si.child_id = c.id) as n_papers
    from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.active
    order by c.section, coalesce(nullif(regexp_replace(c.roll_no, '\D', '', 'g'), '')::int, 9999), c.roll_no`;
}

export async function childHeader(id: string, actor: string): Promise<ChildRow | undefined> {
  const rows = await childrenOnRoll(actor);
  return rows.find((c) => c.id === id);
}

export type RungState = {
  rung_code: string;
  ladder_order: number | null;
  descriptor: string;
  skill_code: string | null;
  state: string | null;
  n_events: number;
  n_correct: number;
  repeating_misconception: string | null;
  last_seen: string | null;
};

// The band's ladder (its three levels) plus any rung the child has evidence on; rungs no paper
// has touched stay "not enough yet" with nothing behind them, which is the honest reading.
export async function childMap(id: string): Promise<RungState[]> {
  return sql<RungState[]>`
    with ladder as (
      select unnest(l.rung_codes) as rung_code from level_rule l join child c on c.band = l.band where c.id = ${id}::uuid
      union select rung_code from child_skill_state where child_id = ${id}::uuid
    )
    select r.code as rung_code, r.ladder_order, r.descriptor, s.skill_code, s.state,
           coalesce(s.n_events, 0)::int as n_events, coalesce(s.n_correct, 0)::int as n_correct,
           s.repeating_misconception, s.last_seen
    from ladder x
    join rung r on r.code = x.rung_code
    left join child_skill_state s on s.child_id = ${id}::uuid and s.rung_code = r.code
    order by r.ladder_order nulls last, r.code`;
}

export type NextStep = { code: string; name: string; rung_code: string; difficulty: string | null; rule: string; targets: string[] };

export async function childNext(id: string): Promise<NextStep[]> {
  return sql<NextStep[]>`
    select s.code, s.name, s.rung_code, n.difficulty, n.rule, coalesce(n.targets, '{}') as targets
    from skill_set s, lateral next_difficulty(${id}::uuid, s.code) n
    order by s.code`;
}

export type PendingResult = {
  id: string;
  paper: string;
  date: string | null;
  item_key: string;
  question: string;
  answer: string | null;
  read: string;
  attempted: boolean;
  working: string;
  status: string;
  misconception_codes: string[];
};

export async function pendingResults(id: string): Promise<PendingResult[]> {
  return sql<PendingResult[]>`
    select r.id, t.key ->> 'title' as paper, t.key ->> 'date' as date, i.item_key,
           i.spec ->> 'question' as question, i.responses -> 0 ->> 'answer' as answer,
           coalesce(r.raw_read::jsonb ->> 'child_answer', '') as read,
           coalesce((r.raw_read::jsonb ->> 'attempted')::boolean, false) as attempted,
           coalesce(r.raw_read::jsonb ->> 'working_summary', '') as working,
           r.status, r.misconception_codes
    from item_result r
    join item i on i.id = r.item_id
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    where si.child_id = ${id}::uuid and r.state = 'candidate'
    order by t.key ->> 'date', i.item_key`;
}

export type Paper = { id: string; title: string; date: string | null; pages: number; status: string; narrative: string | null; n_results: number; n_confirmed: number };

export async function childPapers(id: string): Promise<Paper[]> {
  return sql<Paper[]>`
    select c.id, t.key ->> 'title' as title, t.key ->> 'date' as date, c.pages, c.status,
           (select text from narrative_observation n where n.capture_id = c.id order by n.created_at desc limit 1) as narrative,
           (select count(*)::int from item_result r where r.capture_id = c.id) as n_results,
           (select count(*)::int from item_result r where r.capture_id = c.id and r.state = 'confirmed') as n_confirmed
    from capture c
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    where si.child_id = ${id}::uuid
    order by t.key ->> 'date', c.created_at`;
}
