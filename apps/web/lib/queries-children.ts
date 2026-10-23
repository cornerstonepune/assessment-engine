import { sql } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";
import type { Rag } from "./rag";
import type { States } from "./states";
import { reportState, type ReportState } from "./queries-reports";
import { skillTaughtIn } from "./taught";
import { paperName } from "./queries-papers";

// Children (goals/u2-children.yaml): a grade's classes, a class as its children against every step, and what a
// child's page adds to the graph — the mistakes that repeat and every paper made for or read from the child. The
// states are the engine's (`rebuild_child_skill_state`); nothing here decides one.

/** One row of the Children table (goals/u8-children-table.yaml): a child's standing and next step. */
export type ChildRow = {
  id: string;
  band: string;
  section: string;
  roll_no: string;
  first_name: string;
  /** The skill they most need help on: red before amber, the least often right first, and the mistake they repeat on
   *  it, named for its skill. None when nothing is red or amber. */
  help: { name: string; rag: "red" | "amber"; mistake: string | null } | null;
  /** How many skill sets are red, amber and green. */
  needs_help: number;
  green: number;
  amber: number;
  /** Their answers waiting for a person, on papers not replaced or voided: the papers pages' rule (`queries-papers`). */
  waiting: number;
  /** The score on their newest signed-off paper, "3 of 3 right" (right of every answer marked right, wrong or blank), or none
   *  while no paper of theirs is signed off: the number a person looks for after signing off (goals/chk_whose_paper.yaml). */
  last_score: string | null;
  /** Their newest parent report and whether there are answers to write one from (`queries-reports`). */
  report: ReportState;
};

/** Every child on roll, grade by grade, with their standing on each taught skill — or one taught topic's skills
 *  (goals/ui4b2-class-by-topic.yaml) — as the graph's own states give it (one skill set counted once, in the worst
 *  state of its skills), their answers waiting for a person, and their newest parent report. Names through pii.read_child, which
 *  logs who asked. */
export async function childTable(actor: string, topic: string | null = null, scope: Scope = EVERY_CLASS): Promise<ChildRow[]> {
  return sql<ChildRow[]>`
    with st as (
      select s.child_id, s.rung_code, ss.name,
             min(cs.severity) as sev,
             sum(s.n_correct)::float / nullif(sum(s.n_events), 0) as right_share,
             (array_agg(mistake_name(s.repeating_misconception, s.skill_code))
                filter (where s.repeating_misconception is not null))[1] as mistake
      from child_skill_state s
      join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
      join skill ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code
      join child sc on sc.id = s.child_id
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
        and ${skillTaughtIn(sql`ss.tenant_id`, sql`ss.code`, sql`sc.section`)} ${topic ? sql`and t.code = ${topic}` : sql``}
      group by s.child_id, s.rung_code, ss.name
    ),
    -- a severity's colour and whether a next paper works on it: the states of one severity share both
    sv as (select distinct on (severity) severity, colour, needs_work from child_state order by severity, ord)
    select c.id, c.band, c.section, c.roll_no, p.first_name,
           (select jsonb_build_object('name', st.name, 'rag', sv.colour, 'mistake', st.mistake)
              from st join sv on sv.severity = st.sev where st.child_id = c.id and sv.needs_work
             order by st.sev, st.right_share nulls last, st.name limit 1) as help,
           (select count(*)::int from st join sv on sv.severity = st.sev where st.child_id = c.id and sv.colour = 'red') as needs_help,
           (select count(*)::int from st join sv on sv.severity = st.sev where st.child_id = c.id and sv.colour = 'green') as green,
           (select count(*)::int from st join sv on sv.severity = st.sev where st.child_id = c.id and sv.colour = 'amber') as amber,
           (select count(*)::int from item_result r join capture k on k.id = r.capture_id
              join sheet_instance si on si.id = k.sheet_instance_id
             where si.child_id = c.id and k.superseded_by is null and si.print_status <> 'void'
               and r.status in ('unreadable', 'needs_teacher')) as waiting,
           (select count(*) filter (where r.status = 'correct') || ' of ' ||
                   count(*) filter (where r.status in ('correct', 'wrong', 'blank')) || ' right'
              from item_result r join capture k on k.id = r.capture_id
             where k.sheet_instance_id = (
                     select si.id from sheet_instance si join capture k2 on k2.sheet_instance_id = si.id and k2.superseded_by is null
                      where si.child_id = c.id and si.print_status <> 'void'
                        and exists (select 1 from item_result x where x.capture_id = k2.id and x.state = 'confirmed')
                        and not exists (select 1 from item_result x where x.capture_id = k2.id and x.state = 'candidate')
                      order by k2.created_at desc limit 1)
               and k.superseded_by is null) as last_score,
           ${reportState(sql`c.id`)} as report
    from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.active and ${inScope(scope, sql`c.section`)}
    order by grade_ord(c.tenant_id, c.band), c.section, roll_order(c.roll_no), c.roll_no`;
}

/** One column of the class grid: a rung, for one skill it carries. */
/** One step of the class grid: its skill, and the skill set a paper on it is drawn from, with the levels it has. */
export type Step = {
  skill_code: string;
  skill_name: string;
  rung_code: string;
  descriptor: string;
  topic_code: string;
  topic_name: string;
  skill_set: string;
  levels: string[];
};
export type GridChild = { id: string; roll_no: string; first_name: string; states: Record<string, { state: string; n_events: number; n_correct: number }> };

export const stepKey = (s: { skill_code: string; rung_code: string }) => `${s.skill_code}|${s.rung_code}`;

/** A taught skill of the class's grade no child of it has answered: named once, and checked for the whole class. */
export type Unanswered = { code: string; name: string; levels: string[]; topic_code: string };

/** A class's children in roll order, each name read through pii.read_child, which logs who asked. */
export async function classRoll(section: string, actor: string): Promise<{ id: string; roll_no: string; first_name: string }[]> {
  return sql<{ id: string; roll_no: string; first_name: string }[]>`
    select c.id, c.roll_no, p.first_name from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.active and c.section = ${section}
    order by roll_order(c.roll_no), c.roll_no`;
}


/** The levels of skill set `ss` that a grade uses: its own grade's and those below, each level's grade its row's
 *  (`skill_level.grade`, goals/f1e-the-grade-plan.yaml) — the engine's rule, so a check is never offered at a level a
 *  paper would refuse. */
const levelsUsedBy = (band: ReturnType<typeof sql>) => sql`array(
  select l.difficulty from skill_level l join difficulty d on d.tenant_id = l.tenant_id and d.code = l.difficulty
  where l.tenant_id = ss.tenant_id and l.skill_code = ss.code
    and coalesce(grade_ord(l.tenant_id, l.grade), -1) <= grade_ord(ss.tenant_id, ${band})
  order by d.ord)`;

/** A class against the skills it has been assessed on (goals/v2-what-answers-show.yaml): one column per taught skill
 *  any child in the class has a checked answer on, in the shared tree's order — topic by topic, easy to hard — and
 *  each child's state and score on each. A skill no child has answered is not a column of grey: it is named once,
 *  in `notYet`. Names through pii.read_child. */
export async function classGrid(
  section: string,
  actor: string,
): Promise<{ steps: Step[]; children: GridChild[]; notYet: Unanswered[]; band: string }> {
  const [steps, children, states, notYet, [grade]] = await Promise.all([
    sql<Step[]>`
      select distinct s.skill_code, ss.name as skill_name, ss.rung_code, ss.name as descriptor, t.code as topic_code, t.name as topic_name,
             ss.code as skill_set, ${levelsUsedBy(sql`class_band(ss.tenant_id, ${section})`)} as levels, t.ord, ss.ladder_order
      from child_skill_state s join child c on c.id = s.child_id
      join skill ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code and s.skill_code = any(ss.registry_codes)
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and ${skillTaughtIn(sql`ss.tenant_id`, sql`ss.code`, section)}
      where c.section = ${section} and c.active and s.n_events > 0
      order by t.ord, ss.ladder_order nulls last, ss.rung_code`,
    classRoll(section, actor),
    sql<{ child_id: string; skill_code: string; rung_code: string; state: string; n_events: number; n_correct: number }[]>`
      select s.child_id, s.skill_code, s.rung_code, s.state, s.n_events, s.n_correct
      from child_skill_state s join child c on c.id = s.child_id where c.section = ${section} and c.active`,
    sql<Unanswered[]>`
      select ss.code, ss.name, ${levelsUsedBy(sql`class_band(ss.tenant_id, ${section})`)} as levels, t.code as topic_code from skill ss
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and ${skillTaughtIn(sql`ss.tenant_id`, sql`ss.code`, section)}
      where ss.grade in (select band from child where section = ${section} and active)
        and not exists (select 1 from child_skill_state s join child c on c.id = s.child_id
                        where c.section = ${section} and c.active and s.rung_code = ss.rung_code and s.n_events > 0)
      order by t.ord, ss.ladder_order nulls last`,
    // the class's grade: the database's one rule, which the engine asks too (goals/ux2-one-count-one-thing.yaml)
    sql<{ band: string }[]>`
      select class_band(tenant_id, section) as band from child where section = ${section} and active limit 1`,
  ]);
  return {
    steps,
    children: children.map((c) => ({
      ...c,
      states: Object.fromEntries(states.filter((s) => s.child_id === c.id).map((s) => [stepKey(s), s])),
    })),
    notYet,
    band: grade?.band ?? "",
  };
}

export type ChildSkill = {
  code: string;
  name: string;
  topic: string;
  topic_code: string;
  rung_code: string;
  skill_code: string | null;
  /** The skill's own name: a rung that tests two skills gives its skill set a line for each (`Money`, `Word problems`). */
  skill_name: string | null;
  state: string | null;
  n_events: number;
  n_correct: number;
  repeating_misconception: string | null;
  last_seen: string | null;
  /** The levels its skill set has, for a check on it. */
  levels: string[];
};

/** A child's skills taught in their class (goals/f1f-taught-per-class.yaml): those of their grade, and any other a
 *  checked answer of theirs landed on — each with the graph's state and score, in the shared tree's order. A skill with
 *  no answers has no state. */
export async function childSkills(id: string): Promise<ChildSkill[]> {
  return sql<ChildSkill[]>`
    select ss.code, ss.name, t.name as topic, t.code as topic_code, ss.rung_code, s.skill_code, sk.name as skill_name, s.state,
           ${levelsUsedBy(sql`(select band from child where id = ${id}::uuid)`)} as levels,
           coalesce(s.n_events, 0)::int as n_events, coalesce(s.n_correct, 0)::int as n_correct,
           s.repeating_misconception, s.last_seen
    from skill ss
    join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
      and ${skillTaughtIn(sql`ss.tenant_id`, sql`ss.code`, sql`(select section from child where id = ${id}::uuid)`)}
    left join child_skill_state s on s.child_id = ${id}::uuid and s.rung_code = ss.rung_code and s.skill_code = any(ss.registry_codes)
    left join registry_skill sk on sk.tenant_id = ss.tenant_id and sk.code = s.skill_code
    where ss.grade = (select band from child where id = ${id}::uuid) or s.n_events > 0
    order by t.ord, ss.ladder_order nulls last, ss.code, s.skill_code`;
}

/** The one sentence a child's page opens on: the skills their checked answers reach, counted by colour, red first;
 *  then how many have too few answers to say, and how many of their grade's skills no paper has reached yet. */
export function summary(name: string, assessed: (string | null)[], notYet: number, states: States): string {
  if (!assessed.length) return `${name} has no checked answers yet; this fills in once a paper is read and checked.`;
  const n: Record<Rag, number> = { red: 0, amber: 0, green: 0, grey: 0 };
  for (const s of assessed) n[states.of(s).colour] += 1;
  const skills = (k: number) => `${k} skill${k === 1 ? "" : "s"}`;
  // the first count says "skill"; the rest are read against it
  // each colour in its one word (goals/ux7-phone-and-words.yaml)
  const cw = (c: Rag) => states.colours[c].count_words;
  const said = (
    [
      ["red", `${cw("red")} on`],
      ["amber", `is ${cw("amber")}`],
      ["green", `is ${cw("green")} on`],
    ] as const
  )
    .filter(([c]) => n[c])
    .map(([c, words], i) => `${words} ${i ? n[c] : skills(n[c])}`);
  const joined = said.length ? inWords(said) : "";
  const few = n.grey ? `${skills(n.grey)} ${n.grey === 1 ? "has" : "have"} too few answers to say` : "";
  const lead = joined ? `${name} ${joined}` : `${name} has answers on ${skills(n.grey)}, too few to say yet`;
  const rest = [joined && few, notYet ? `${skills(notYet)} of the grade not assessed yet` : ""].filter(Boolean);
  return `${lead}${rest.length ? `; ${rest.join("; ")}` : ""}.`;
}

/** A list as a sentence says it: "a", "a and b", "a, b and c". */
export const inWords = (xs: string[]) => (xs.length > 1 ? `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}` : (xs[0] ?? ""));

/** What a child with no checked answer and nothing waiting on a person is told, and the one thing to do
 *  (goals/ux4-class-and-child.yaml): the papers already made for them that wait to be approved or read — the one, or
 *  every one of them on Assessments; a check besides would be a paper too many — else the first check that would place
 *  them. None when their class is taught nothing of their grade yet: there is no check to make. */
export function firstStep(
  name: string,
  waits: ChildSheet[],
  allPapers: string,
  check: { skills: string[]; n: number; href: string },
): { said: string; action: { words: string; href: string } | null } {
  if (waits.length > 1) {
    return {
      said: `${name} has no checked answers yet: ${waits.length} papers made for ${name} wait to be approved or read.`,
      action: { words: `See ${name}’s ${waits.length} papers →`, href: allPapers },
    };
  }
  if (waits.length) {
    const [w] = waits;
    const what = `${(w.kind && PURPOSE[w.kind]) || "paper"} ${w.qr_code}`;
    return {
      said: `${name} has no checked answers yet: ${what} waits to be ${w.print_status === "new" ? "approved" : "read"}.`,
      action: { words: `Open paper ${w.qr_code} →`, href: `/worksheets/${w.qr_code}` },
    };
  }
  if (!check.skills.length) return { said: `${name} has no checked answers yet, and their class is taught no skill of their grade yet.`, action: null };
  return {
    said: `${name} has no checked answers yet: a first check of ${check.n} questions on each of ${inWords(check.skills)} shows where ${name} stands.`,
    action: { words: `Make ${name}’s first check →`, href: check.href },
  };
}

/** The skills a class has checked answers on, the latest first: what a child new to its work is checked on first. */
export async function classLatest(section: string): Promise<string[]> {
  const rows = await sql<{ code: string }[]>`
    select ss.code from child_skill_state s
    join child c on c.id = s.child_id and c.section = ${section}
    join skill ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code
    where s.n_events > 0
    group by ss.code order by max(s.last_seen) desc, ss.code`;
  return rows.map((r) => r.code);
}

export type Repeated = { code: string; name: string; skill_name: string; descriptor: string; rung_code: string; skill_code: string; times: number };

/** Every mistake the graph found repeating on one of the child's steps, with how often it showed on that step. */
export async function repeatedMistakes(id: string): Promise<Repeated[]> {
  return sql<Repeated[]>`
    select s.repeating_misconception as code, coalesce(m.name, s.repeating_misconception) as name,
           coalesce(k.name, s.skill_code) as skill_name, r.descriptor, s.rung_code, s.skill_code,
           (select count(*)::int from evidence_placed e
              left join item_result ir on ir.id = e.item_result_id left join capture c on c.id = ir.capture_id
             where e.child_id = s.child_id and e.skill_code = s.skill_code and e.rung_code = s.rung_code
               and e.confirmed_by is not null and (c.id is null or c.superseded_by is null)
               and s.repeating_misconception = any(e.misconception_codes)) as times
    from child_skill_state s
    join skill r on r.tenant_id = s.tenant_id and r.rung_code = s.rung_code
    left join lateral (select name from registry_skill where code = s.skill_code limit 1) k on true
    left join lateral (select mistake_name(s.repeating_misconception, s.skill_code) as name) m on true
    where s.child_id = ${id}::uuid and s.repeating_misconception is not null
    order by times desc, r.ladder_order`;
}

export type ChildSheet = {
  id: string;
  qr_code: string;
  kind: string | null;
  week: string | null;
  title: string | null;
  date: string | null;
  print_status: string;
  approved_by: string | null;
  approved_at: string | null;
  n_results: number;
  n_confirmed: number;
};

/** Every paper made for the child or read from them, newest first: its purpose, who approved it, what was read. */
export async function childSheets(id: string): Promise<ChildSheet[]> {
  return sql<ChildSheet[]>`
    select si.id, si.qr_code, si.kind, coalesce(si.week, st.week) as week, ${paperName("st")} as title,
           st.key ->> 'date' as date, si.print_status, si.approved_by, si.approved_at,
           (select count(*)::int from item_result r join capture c on c.id = r.capture_id
             where c.sheet_instance_id = si.id and c.superseded_by is null) as n_results,
           (select count(*)::int from item_result r join capture c on c.id = r.capture_id
             where c.sheet_instance_id = si.id and c.superseded_by is null and r.state = 'confirmed') as n_confirmed
    from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id
    where si.child_id = ${id}::uuid and si.print_status <> 'void'
    order by coalesce(st.key ->> 'date', si.created_at::date::text) desc, si.created_at desc`;
}

/** What each kind of paper is for, in the school's words. A paper read before QR sheets has no kind. */
export const PURPOSE: Record<string, string> = {
  assessment: "class assessment",
  practice: "class practice",
  focus: "their home assessment",
  custom: "their home assessment, chosen by their educator",
  home: "sent home",
};
