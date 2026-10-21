import { cache } from "react";
import { sql, TENANT_SLUG } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";
import { skillTaughtFor, skillTaughtIn } from "./taught";

/** A level's name, a row of `difficulty` (lib/levels.ts). */
export type Difficulty = string;

export type Band = { words: string; check: Record<string, unknown> };

/** The levels a skill defines, in the table's order (`levelsColumn`): most have all four, some fewer (1-digit −
 *  1-digit has no Hard). */
export const levelsOf = (s: { levels: Difficulty[] }) => s.levels;

/** `levels` of a skill set row `s`, for a query to select: the levels its rule defines, in the table's order. A
 *  function, so importing this file never touches the database. */
export const levelsColumn = () => sql`coalesce((select array_agg(d.code order by d.ord) from difficulty d
                                        where d.tenant_id = s.tenant_id and s.difficulty ? d.code), '{}') as levels`;

/** The grade a skill's level belongs to: one grade each — named in `level_band`, else the skill's own. */
export const gradeOf = (s: { band: string; level_band?: Partial<Record<Difficulty, string>> }, d: Difficulty) =>
  s.level_band?.[d] ?? s.band;

export type Grade = { code: string; name: string; ord: number };
/** The school's grades in their order, and each one's name and place (goals/b0b-grades-from-the-table.yaml). */
export type Grades = { list: Grade[]; name: (code: string) => string; ord: (code: string) => number };

/** The school's grades, as the `grade` table holds them: read once a request, by every page that names or orders one.
 *  A grade's place is its row's order, never a number read from its code ("G10" is not Grade 1). */
export const grades = cache(async (): Promise<Grades> => {
  const list = await sql<Grade[]>`
    select g.code, g.name, g.ord from grade g join tenant t on t.id = g.tenant_id and t.slug = ${TENANT_SLUG} order by g.ord`;
  const by = new Map(list.map((g) => [g.code, g]));
  return { list, name: (code) => by.get(code)?.name ?? code, ord: (code) => by.get(code)?.ord ?? -1 };
});

/** The grades the curriculum runs over, as the menu says them: its lowest and highest grade that a skill is in. */
export async function gradeSpan(): Promise<string> {
  const rows = await sql<{ name: string }[]>`
    select g.name from grade g join tenant t on t.id = g.tenant_id and t.slug = ${TENANT_SLUG}
    where exists (select 1 from rung r where r.tenant_id = g.tenant_id and r.band = g.code)
    order by g.ord`;
  return [...new Set([rows[0]?.name, rows.at(-1)?.name])].filter(Boolean).join("–");
}

/** Whether a class or child of `band` uses this level: its own grade's levels and those of the grades below
 *  (goals/f1e-the-grade-plan.yaml) — as the engine gives and refuses them (`shelf._levels`). */
export const usesLevel = (g: Grades, s: { band: string; level_band?: Partial<Record<Difficulty, string>> }, d: Difficulty, band: string) =>
  g.ord(gradeOf(s, d)) <= g.ord(band);

export type SkillSet = {
  code: string;
  rung_code: string;
  name: string;
  learning_objective: string;
  philosophy: string[];
  formats: string[];
  misconception_codes: string[];
  difficulty: Record<Difficulty, Band>;
  levels: Difficulty[];
  status: "draft" | "ratified";
  ratified_by: string | null;
  /** Each level whose questions a person approved, with who and when (goals/f1d-questions-approved-per-level.yaml). */
  level_approved: Partial<Record<Difficulty, { by: string; at: string }>>;
  updated_at: string;
  band: string;
  /** The grade each level belongs to, where it is not the skill's own (`skill_set.level_band`). */
  level_band: Partial<Record<Difficulty, string>>;
  /** Who last moved a level to another grade, and when (goals/c1-whole-curriculum.yaml). */
  level_band_by: string | null;
  level_band_at: string | null;
  descriptor: string;
  skill_codes: string[];
  version: number;
  counts: Partial<Record<Difficulty, number>>;
  // Ready-made worksheets per level (ADR 0026). None until the library is built.
  worksheets: Partial<Record<Difficulty, number>>;
  // Its place in the shared tree: grade (band) → subject → topic → skill → level (goals/t1-topics.yaml).
  topic_code: string | null;
  topic_name: string | null;
  topic_ord: number | null;
  /** Whether its topic is taught in the class asked about, or in any class of the scope (goals/f1f-taught-per-class.yaml). */
  taught: boolean;
};

/** The skills taught in a class (`section`), or in any class of the scope — a topic not taught there is not on the screen
 *  (goals/v1-only-what-is-taught.yaml, goals/f1f-taught-per-class.yaml) — or, with `untaught`, every skill: one is read
 *  and approved before its topic is taught, on its own page and the approval page (goals/ny1-needs-you.yaml). */
export async function skillSets({
  untaught = false,
  scope = EVERY_CLASS,
  section,
}: { untaught?: boolean; scope?: Scope; section?: string } = {}): Promise<SkillSet[]> {
  const taught = section ? skillTaughtIn(sql`s.tenant_id`, sql`s.code`, section) : skillTaughtFor(scope, sql`s.tenant_id`, sql`s.code`);
  return sql<SkillSet[]>`
    select s.code, s.rung_code, s.name, s.learning_objective, s.philosophy, s.formats,
           s.misconception_codes, s.difficulty, ${levelsColumn()}, s.status, s.ratified_by, s.level_approved, s.updated_at, s.version,
           r.band, coalesce(s.level_band, '{}'::jsonb) as level_band, s.level_band_by, s.level_band_at, r.descriptor, r.skill_codes, s.topic_code,
           t.name as topic_name, t.ord as topic_ord, ${taught} as taught,
           coalesce((select json_object_agg(d.difficulty, d.n)
                     from (select difficulty, count(*)::int as n from item
                           where item.skill_set_code = s.code and item.status = 'active' and item.source = 'generated'
                           group by difficulty) d), '{}'::json) as counts,
           coalesce((select json_object_agg(w.difficulty, w.n)
                     from (select difficulty, count(*)::int as n from sheet_template t
                           where t.skill_set_code = s.code and t.source = 'library' and t.retired_at is null
                           group by difficulty) w), '{}'::json) as worksheets
    from skill_set s
    join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    left join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code
    where ${untaught} or ${taught}
    order by r.ladder_order nulls last, s.code`;
}

export async function skillSet(code: string, scope: Scope = EVERY_CLASS): Promise<SkillSet | undefined> {
  const rows = await skillSets({ untaught: true, scope });
  return rows.find((s) => s.code === code);
}

export type Skill = { code: string; name: string; description: string; rungs: string[] };

/** The registry's skills a skill set practises — each reached through its rung, the way to its topic and so to its
 *  subject — with the rungs that carry it. */
export async function setSkills(): Promise<Skill[]> {
  return sql<Skill[]>`
    select k.code, k.name, k.description,
           coalesce(array_agg(r.code order by r.ladder_order) filter (where r.code is not null), '{}') as rungs
    from skill k
    left join rung r on r.tenant_id = k.tenant_id and k.code = any(r.skill_codes)
    where exists (select 1 from skill_set ss join rung sr on sr.tenant_id = ss.tenant_id and sr.code = ss.rung_code
                  where ss.tenant_id = k.tenant_id and k.code = any(sr.skill_codes))
    group by k.code, k.name, k.description
    order by k.code`;
}

// Every mistake's name for each operation, for each operation's skill, and for neither, by the database's one rule
// (`mistakeName` reads it).
export async function misconceptionNames(): Promise<Record<string, string>> {
  const rows = await sql<{ key: string; name: string }[]>`
    with codes as (select distinct code from misconception),
         ops as (select e.key as op, e.value as skill from config c, jsonb_each_text(c.value) e where c.key = 'skills.by_operation')
    select codes.code || '@' || ops.op as key, mistake_name(codes.code, null, ops.op) as name from codes, ops
    union all
    select codes.code || '|' || ops.skill, mistake_name(codes.code, ops.skill) from codes, ops
    union all
    select code, mistake_name(code, null) from codes`;
  return Object.fromEntries(rows.map((r) => [r.key, r.name]));
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

export const RULE_WORDS: Record<string, string> = {
  band_default: "Not enough of their own work yet, so this is the starting level for their grade.",
  from_state: "From what this child's last papers showed.",
  override: "A teacher set this by hand.",
};

// `classes`: the classes a person teaches, as `engine staff add --class` puts them (ADR 0073, D1); the coordinator's are every class.
export type Staff = { email: string; name: string; role: string; password?: string; classes?: string[] };

export async function staffList(): Promise<Staff[]> {
  const row = await sql<{ value: Staff[] }[]>`select value from config where key = 'app.staff'`;
  return row[0]?.value ?? [];
}

// ---- Child Growth: what confirmed evidence says about one child, and what still waits for a person.

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

// Every name read goes through pii.read_child, which logs who asked (rule 6); so a name is read only for a child the page
// shows — the classes the person sees, or the one child it is about (goals/ux1-who-sees-what.yaml). The rows are chosen
// before any name is read: `where` names `c` alone, and is applied as `child` is scanned, ahead of the logged accessor.
async function childRows(actor: string, where: ReturnType<typeof inScope>): Promise<ChildRow[]> {
  return sql<ChildRow[]>`
    select c.id, c.roll_no, c.section, c.band, p.first_name,
           (select count(*)::int from answer_placed e
              left join item_result r on r.id = e.item_result_id left join capture k on k.id = r.capture_id
             where e.child_id = c.id and e.confirmed_by is not null and (k.id is null or k.superseded_by is null)) as n_events,
           (select count(*)::int from item_result r join capture k on k.id = r.capture_id
              join sheet_instance si on si.id = k.sheet_instance_id
             where si.child_id = c.id and r.state = 'candidate' and k.superseded_by is null) as n_pending,
           (select count(*)::int from capture k join sheet_instance si on si.id = k.sheet_instance_id
             where si.child_id = c.id and k.superseded_by is null) as n_papers
    from (select * from child c where c.active and ${where}) c, lateral pii.read_child(c.id, ${actor}) p
    order by c.section, roll_order(c.roll_no), c.roll_no`;
}

/** The children on the roll of the classes a person sees, each name read in their name. */
export async function childrenOnRoll(actor: string, scope: Scope): Promise<ChildRow[]> {
  return childRows(actor, inScope(scope, sql`c.section`));
}

/** One child on the roll, the only name read. */
export async function childHeader(id: string, actor: string): Promise<ChildRow | undefined> {
  const [row] = await childRows(actor, sql`c.id = ${id}::uuid`);
  return row;
}

export type NextStep = { code: string; name: string; rung_code: string; difficulty: string | null; rule: string; targets: string[] };

export async function childNext(id: string): Promise<NextStep[]> {
  return sql<NextStep[]>`
    select s.code, s.name, s.rung_code, n.difficulty, n.rule, coalesce(n.targets, '{}') as targets
    from skill_set s, lateral next_difficulty(${id}::uuid, s.code) n
    where ${skillTaughtIn(sql`s.tenant_id`, sql`s.code`, sql`(select section from child where id = ${id}::uuid)`)}
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
  // what a mistake on it is named for: its operation, else the skill each mistake was charged to, else its own skill
  op: string | null;
  mistake_skills: Record<string, string> | null;
  skill_code: string;
  capture_id: string;
  paper_id: string;
  page: number;
  file_page: number;
  box: number[] | null;
};

export async function pendingResults(id: string): Promise<PendingResult[]> {
  return sql<PendingResult[]>`
    select r.id, coalesce(t.key ->> 'title', t.code) as paper, coalesce(t.key ->> 'date', c.created_at::date::text) as date,
           i.item_key, coalesce(i.spec ->> 'question', i.stem) as question, result_response(i.responses, r.rid) ->> 'answer' as answer,
           r.capture_id, si.id as paper_id,
           coalesce((r.raw_read::jsonb ->> 'page')::int, (i.spec ->> 'page')::int, 1) as page,
           coalesce((r.raw_read::jsonb ->> 'file_page')::int, (r.raw_read::jsonb ->> 'page')::int, (i.spec ->> 'page')::int, 1) as file_page,
           case when jsonb_typeof(r.raw_read::jsonb -> 'box') = 'array'
                then array(select jsonb_array_elements_text(r.raw_read::jsonb -> 'box'))::numeric[] end as box,
           coalesce(r.raw_read::jsonb ->> 'child_answer', '') as read,
           coalesce((r.raw_read::jsonb ->> 'attempted')::boolean, false) as attempted,
           coalesce(r.raw_read::jsonb ->> 'working_summary', '') as working,
           r.status, r.misconception_codes, i.skill_codes[1] as skill_code,
           operation_sign(i.spec ->> 'op') as op, i.mistake_skills
    from item_result r
    join item i on i.id = r.item_id
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    where si.child_id = ${id}::uuid and r.state = 'candidate' and c.superseded_by is null
    order by t.key ->> 'date', si.id, page, i.item_key`;
}

export type Evidence = {
  rung_code: string;
  skill_code: string;
  date: string | null;
  paper: string;
  item_key: string;
  question: string;
  answer: string | null;
  read: string;
  working: string;
  status: string;
  misconception_codes: string[];
  // the question's operation, as `operation_sign` folds it: what its mistakes are named for, before `skill_code`
  op: string | null;
};

// Every confirmed answer, with the question and what the child wrote, so a rung's state can be
// opened up to the work it rests on.
export async function childEvidence(id: string): Promise<Evidence[]> {
  return sql<Evidence[]>`
    select coalesce(i.rung_code, e.rung_code) as rung_code, e.skill_code, t.key ->> 'date' as date, coalesce(t.key ->> 'title', t.code) as paper, i.item_key,
           coalesce(i.spec ->> 'question', i.stem) as question,
           coalesce(i.spec ->> 'answer', result_response(i.responses, r.rid) ->> 'answer') as answer,
           coalesce(r.raw_read::jsonb ->> 'child_answer', '') as read,
           coalesce(r.raw_read::jsonb ->> 'working_summary', '') as working,
           r.status, e.misconception_codes, operation_sign(i.spec ->> 'op') as op
    from evidence_placed e
    join item_result r on r.id = e.item_result_id
    join item i on i.id = r.item_id
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    where e.child_id = ${id}::uuid and e.confirmed_by is not null and c.superseded_by is null
    order by t.key ->> 'date', i.item_key`;
}

export type Paper = { id: string; sheet: string; title: string; date: string | null; pages: number; status: string; narrative: string | null; n_results: number; n_confirmed: number };

export async function childPapers(id: string): Promise<Paper[]> {
  return sql<Paper[]>`
    select c.id, si.id as sheet, coalesce(t.key ->> 'title', t.code) as title, t.key ->> 'date' as date, c.pages, c.status,
           (select text from narrative_observation n where n.capture_id = c.id order by n.created_at desc limit 1) as narrative,
           (select count(*)::int from item_result r where r.capture_id = c.id) as n_results,
           (select count(*)::int from item_result r where r.capture_id = c.id and r.state = 'confirmed') as n_confirmed
    from capture c
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    where si.child_id = ${id}::uuid and c.superseded_by is null
    order by t.key ->> 'date', c.created_at`;
}
