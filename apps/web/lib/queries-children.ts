import { sql } from "./db";
import { rag, type Rag } from "./rag";

// Children (goals/u2-children.yaml): a grade's classes, a class as its children against every step, and what a
// child's page adds to the graph — the mistakes that repeat and every paper made for or read from the child. The
// states are the engine's (`rebuild_child_skill_state`); nothing here decides one.

export type ClassRow = { band: string; section: string; n: number; cells: Record<Rag, number> };

/** Each class on roll with its grade, and how many of its children's seen steps are in each colour. */
export async function classes(): Promise<ClassRow[]> {
  const rows = await sql<{ band: string; section: string; n: number; states: Record<string, number> | null }[]>`
    select c.band, c.section, count(distinct c.id)::int as n,
           (select json_object_agg(state, k) from (
              select s.state, count(*)::int as k from child_skill_state s join child x on x.id = s.child_id
              where x.active and x.section = c.section and x.band = c.band group by s.state) t) as states
    from child c where c.active
    group by c.band, c.section
    order by c.band, c.section`;
  return rows.map((r) => {
    const cells: Record<Rag, number> = { red: 0, amber: 0, green: 0, grey: 0 };
    for (const [state, k] of Object.entries(r.states ?? {})) cells[rag(state)] += k;
    return { band: r.band, section: r.section, n: r.n, cells };
  });
}

/** One column of the class grid: a rung, for one skill it carries. */
export type Step = { skill_code: string; skill_name: string; rung_code: string; descriptor: string; topic_name: string };
export type GridChild = { id: string; roll_no: string; first_name: string; states: Record<string, { state: string; n_events: number; n_correct: number }> };

export const stepKey = (s: { skill_code: string; rung_code: string }) => `${s.skill_code}|${s.rung_code}`;

/** The class's steps — its grades' ladders, each rung once for every skill it carries, and any step a child has
 *  answers on — in the shared tree's order: topic by topic, each skill easy to hard; and each child's state on each.
 *  Names through pii.read_child. */
export async function classGrid(section: string, actor: string): Promise<{ steps: Step[]; children: GridChild[] }> {
  const [steps, children, states] = await Promise.all([
    sql<Step[]>`
      with rungs as (
        select unnest(l.rung_codes) as rung_code from level_rule l
        where l.band in (select band from child where section = ${section} and active)
        union select s.rung_code from child_skill_state s join child c on c.id = s.child_id
        where c.section = ${section} and c.active
      ), pairs as (
        select k as skill_code, r.code as rung_code from rungs x join rung r on r.code = x.rung_code, unnest(r.skill_codes) k
        union select s.skill_code, s.rung_code from child_skill_state s join child c on c.id = s.child_id
        where c.section = ${section} and c.active
      )
      select p.skill_code, coalesce(k.name, p.skill_code) as skill_name, p.rung_code,
             coalesce(ss.name, r.descriptor) as descriptor, coalesce(t.name, 'Other') as topic_name
      from pairs p join rung r on r.code = p.rung_code
      left join lateral (select name from skill where code = p.skill_code limit 1) k on true
      left join lateral (select name, topic_code from skill_set where rung_code = p.rung_code limit 1) ss on true
      left join topic t on t.code = ss.topic_code
      order by t.ord nulls last, r.ladder_order nulls last, r.code, p.skill_code`,
    sql<{ id: string; roll_no: string; first_name: string }[]>`
      select c.id, c.roll_no, p.first_name from child c, lateral pii.read_child(c.id, ${actor}) p
      where c.active and c.section = ${section}
      order by coalesce(nullif(regexp_replace(c.roll_no, '\D', '', 'g'), '')::int, 9999), c.roll_no`,
    sql<{ child_id: string; skill_code: string; rung_code: string; state: string; n_events: number; n_correct: number }[]>`
      select s.child_id, s.skill_code, s.rung_code, s.state, s.n_events, s.n_correct
      from child_skill_state s join child c on c.id = s.child_id where c.section = ${section} and c.active`,
  ]);
  return {
    steps,
    children: children.map((c) => ({
      ...c,
      states: Object.fromEntries(states.filter((s) => s.child_id === c.id).map((s) => [stepKey(s), s])),
    })),
  };
}

/** The one sentence a child's page opens on: the steps their graph shows, counted by colour, red first. */
export function summary(name: string, states: (string | null)[]): string {
  const n: Record<Rag, number> = { red: 0, amber: 0, green: 0, grey: 0 };
  for (const s of states) n[rag(s)] += 1;
  if (n.grey === states.length) return `${name} has no checked answers yet; the graph fills in once a paper is read and checked.`;
  const steps = (k: number) => `${k} step${k === 1 ? "" : "s"}`;
  // the first count says "step"; the rest are read against it
  const said = (
    [
      ["red", "needs help on"],
      ["amber", "is practising"],
      ["green", "has got"],
    ] as const
  )
    .filter(([c]) => n[c])
    .map(([c, words], i) => `${words} ${i ? n[c] : steps(n[c])}`);
  const joined = said.length > 1 ? `${said.slice(0, -1).join(", ")} and ${said.at(-1)}` : said[0];
  const grey = n.grey ? `; ${steps(n.grey)} ${n.grey === 1 ? "has" : "have"} too few answers to say` : "";
  return `${name} ${joined}${grey}.`;
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
    select si.id, si.qr_code, si.kind, coalesce(si.week, st.week) as week, st.key ->> 'title' as title,
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
