import { sql } from "./db";
import { rag, type Rag } from "./rag";

// Children (goals/u2-children.yaml): a grade's classes, a class as its children against every step, and what a
// child's page adds to the graph — the mistakes that repeat and every paper made for or read from the child. The
// states are the engine's (`rebuild_child_skill_state`); nothing here decides one.

export type ClassRow = {
  band: string;
  section: string;
  n: number;
  /** Children, not skills: each child counted once, in the colour of the skill they most need help on. */
  kids: Record<Rag, number>;
  /** The skills the most children need help on, and how many. */
  weakest: { name: string; n: number }[];
  /** Answers read from the class's papers that wait for a person. */
  waiting: number;
  /** The last day a paper of the class was read. */
  last_read: string | null;
};

const WORST: Rag[] = ["red", "amber", "green", "grey"];

/** Each class on roll with its grade: how many of its children stand in each colour (a child in the colour of the
 *  skill they most need help on, grey with no checked answers), the skills the most children need help on, what
 *  waits on Marking, and when a paper was last read. Taught skills only — as the child's own page shows them. */
export async function classes(): Promise<ClassRow[]> {
  const [kids, weak] = await Promise.all([
    sql<{ band: string; section: string; states: string[] | null; waiting: number; last_read: string | null }[]>`
      select c.band, c.section,
             (select array_agg(s.state) from child_skill_state s
               where s.child_id = c.id and exists (
                 select 1 from skill_set ss join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
                 where ss.rung_code = s.rung_code and t.taught)) as states,
             (select count(*)::int from item_result r join capture k on k.id = r.capture_id
                join sheet_instance si on si.id = k.sheet_instance_id
               where si.child_id = c.id and r.state = 'candidate' and k.superseded_by is null) as waiting,
             (select max(k.created_at)::date::text from capture k join sheet_instance si on si.id = k.sheet_instance_id
               where si.child_id = c.id and k.superseded_by is null) as last_read
      from child c where c.active order by c.band, c.section`,
    sql<{ section: string; name: string; n: number }[]>`
      select c.section, ss.name, count(distinct c.id)::int as n
      from child_skill_state s join child c on c.id = s.child_id and c.active
      join skill_set ss on ss.rung_code = s.rung_code
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and t.taught
      where s.state in ('patterned_error', 'emerging')
      group by c.section, ss.name order by c.section, n desc, ss.name`,
  ]);
  const out = new Map<string, ClassRow>();
  for (const k of kids) {
    const row = out.get(k.section) ?? {
      band: k.band, section: k.section, n: 0, kids: { red: 0, amber: 0, green: 0, grey: 0 },
      weakest: weak.filter((w) => w.section === k.section).slice(0, 3).map(({ name, n }) => ({ name, n })),
      waiting: 0, last_read: null,
    }; // prettier-ignore
    const colours = new Set((k.states ?? []).map((st) => rag(st)));
    const worst = WORST.find((c) => c !== "grey" && colours.has(c)) ?? "grey";
    row.n += 1;
    row.kids[worst] += 1;
    row.waiting += k.waiting;
    if (k.last_read && (!row.last_read || k.last_read > row.last_read)) row.last_read = k.last_read;
    out.set(k.section, row);
  }
  return [...out.values()];
}

/** One column of the class grid: a rung, for one skill it carries. */
export type Step = { skill_code: string; skill_name: string; rung_code: string; descriptor: string; topic_name: string };
export type GridChild = { id: string; roll_no: string; first_name: string; states: Record<string, { state: string; n_events: number; n_correct: number }> };

export const stepKey = (s: { skill_code: string; rung_code: string }) => `${s.skill_code}|${s.rung_code}`;

/** A class against the skills it has been assessed on (goals/v2-what-answers-show.yaml): one column per taught skill
 *  any child in the class has a checked answer on, in the shared tree's order — topic by topic, easy to hard — and
 *  each child's state and score on each. A skill no child has answered is not a column of grey: it is named once,
 *  in `notYet`. Names through pii.read_child. */
export async function classGrid(
  section: string,
  actor: string,
): Promise<{ steps: Step[]; children: GridChild[]; notYet: string[] }> {
  const [steps, children, states, notYet] = await Promise.all([
    sql<Step[]>`
      select distinct s.skill_code, ss.name as skill_name, r.code as rung_code, ss.name as descriptor, t.name as topic_name,
             t.ord, r.ladder_order
      from child_skill_state s join child c on c.id = s.child_id
      join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code and s.skill_code = any(r.skill_codes)
      join skill_set ss on ss.tenant_id = r.tenant_id and ss.rung_code = r.code
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and t.taught
      where c.section = ${section} and c.active and s.n_events > 0
      order by t.ord, r.ladder_order nulls last, r.code`,
    sql<{ id: string; roll_no: string; first_name: string }[]>`
      select c.id, c.roll_no, p.first_name from child c, lateral pii.read_child(c.id, ${actor}) p
      where c.active and c.section = ${section}
      order by coalesce(nullif(regexp_replace(c.roll_no, '\D', '', 'g'), '')::int, 9999), c.roll_no`,
    sql<{ child_id: string; skill_code: string; rung_code: string; state: string; n_events: number; n_correct: number }[]>`
      select s.child_id, s.skill_code, s.rung_code, s.state, s.n_events, s.n_correct
      from child_skill_state s join child c on c.id = s.child_id where c.section = ${section} and c.active`,
    sql<{ name: string }[]>`
      select ss.name from skill_set ss
      join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and t.taught
      join rung r on r.tenant_id = ss.tenant_id and r.code = ss.rung_code
      where r.band in (select band from child where section = ${section} and active)
        and not exists (select 1 from child_skill_state s join child c on c.id = s.child_id
                        where c.section = ${section} and c.active and s.rung_code = r.code and s.n_events > 0)
      order by t.ord, r.ladder_order nulls last`,
  ]);
  return {
    steps,
    children: children.map((c) => ({
      ...c,
      states: Object.fromEntries(states.filter((s) => s.child_id === c.id).map((s) => [stepKey(s), s])),
    })),
    notYet: notYet.map((n) => n.name),
  };
}

export type ChildSkill = {
  code: string;
  name: string;
  topic: string;
  rung_code: string;
  skill_code: string | null;
  state: string | null;
  n_events: number;
  n_correct: number;
  repeating_misconception: string | null;
  last_seen: string | null;
};

/** A child's taught skills: those of their grade, and any other a checked answer of theirs landed on — each with the
 *  graph's state and score, in the shared tree's order. A skill with no answers has no state. */
export async function childSkills(id: string): Promise<ChildSkill[]> {
  return sql<ChildSkill[]>`
    select ss.code, ss.name, t.name as topic, r.code as rung_code, s.skill_code, s.state,
           coalesce(s.n_events, 0)::int as n_events, coalesce(s.n_correct, 0)::int as n_correct,
           s.repeating_misconception, s.last_seen
    from skill_set ss
    join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and t.taught
    join rung r on r.tenant_id = ss.tenant_id and r.code = ss.rung_code
    left join child_skill_state s on s.child_id = ${id}::uuid and s.rung_code = r.code and s.skill_code = any(r.skill_codes)
    where r.band = (select band from child where id = ${id}::uuid) or s.n_events > 0
    order by t.ord, r.ladder_order nulls last, ss.code`;
}

/** The one sentence a child's page opens on: the skills their checked answers reach, counted by colour, red first;
 *  then how many have too few answers to say, and how many of their grade's skills no paper has reached yet. */
export function summary(name: string, assessed: (string | null)[], notYet: number): string {
  if (!assessed.length) return `${name} has no checked answers yet; this fills in once a paper is read and checked.`;
  const n: Record<Rag, number> = { red: 0, amber: 0, green: 0, grey: 0 };
  for (const s of assessed) n[rag(s)] += 1;
  const skills = (k: number) => `${k} skill${k === 1 ? "" : "s"}`;
  // the first count says "skill"; the rest are read against it
  const said = (
    [
      ["red", "needs help on"],
      ["amber", "is practising"],
      ["green", "has got"],
    ] as const
  )
    .filter(([c]) => n[c])
    .map(([c, words], i) => `${words} ${i ? n[c] : skills(n[c])}`);
  const joined = said.length > 1 ? `${said.slice(0, -1).join(", ")} and ${said.at(-1)}` : said[0];
  const few = n.grey ? `${skills(n.grey)} ${n.grey === 1 ? "has" : "have"} too few answers to say` : "";
  const lead = joined ? `${name} ${joined}` : `${name} has answers on ${skills(n.grey)}, too few to say yet`;
  const rest = [joined && few, notYet ? `${skills(notYet)} of the grade not assessed yet` : ""].filter(Boolean);
  return `${lead}${rest.length ? `; ${rest.join("; ")}` : ""}.`;
}

export type Repeated = { code: string; name: string; skill_name: string; descriptor: string; rung_code: string; skill_code: string; times: number };

/** Every mistake the graph found repeating on one of the child's steps, with how often it showed on that step. */
export async function repeatedMistakes(id: string): Promise<Repeated[]> {
  return sql<Repeated[]>`
    select s.repeating_misconception as code, coalesce(m.name, s.repeating_misconception) as name,
           coalesce(k.name, s.skill_code) as skill_name, r.descriptor, s.rung_code, s.skill_code,
           (select count(*)::int from evidence_event e
              left join item_result ir on ir.id = e.item_result_id left join capture c on c.id = ir.capture_id
             where e.child_id = s.child_id and e.skill_code = s.skill_code and e.rung_code = s.rung_code
               and e.confirmed_by is not null and (c.id is null or c.superseded_by is null)
               and s.repeating_misconception = any(e.misconception_codes)) as times
    from child_skill_state s
    join rung r on r.code = s.rung_code
    left join lateral (select name from skill where code = s.skill_code limit 1) k on true
    left join lateral (select name from misconception where code = s.repeating_misconception order by op = 'any' desc limit 1) m on true
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
    select si.id, si.qr_code, si.kind, coalesce(si.week, st.week) as week, coalesce(st.key ->> 'title', st.code) as title,
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
  focus: "their own next paper",
  home: "sent home",
};
