import { sql } from "./db";
import { seesClassIn, seesSheet, type Who } from "./reach";
import type { Rag } from "./rag";
import { skillTaughtIn } from "./taught";
import { paperName } from "./queries-papers";

// Results by topic (goals/res_results_by_topic.yaml). Nimish, 24 Oct 2026: "The unit of reference is the topic: Subject,
// then Topic, then Skill, then difficulty levels." Every number here is read from the graph's own states
// (`child_skill_state`, rebuilt from signed-off answers only) and from signed-off answers on readings nobody replaced;
// nothing is estimated and nothing decides a state. A group of skills (a topic, a skill set) takes the state of its
// weakest skill, by the severity its `child_state` row gives it, as the Children table always has (`childTable`).
// Each level of the class view is one query, run only when it is opened.

type Fragment = ReturnType<typeof sql>;

/** How many children are in each colour, and how many have no checked answer at all (`none`). */
export type Spread = Record<Rag | "none", number>;

/** The three signals of a set of answers (rule 5): never folded into "incorrect". */
export type Signals = { right: number; wrong: number; wrong_working: number; blank: number };

/** The skills a class is taught that its results are read over: taught in it (`skill_taught_in`), of its grade or with a
 *  checked answer of one of its children on them, as a child's page reads its own (`childSkills`). */
const classSkills = (section: string) => sql`
  select ss.tenant_id, ss.code, ss.name, ss.rung_code, ss.registry_codes, ss.topic_code, ss.ladder_order
  from skill ss
  where ${skillTaughtIn(sql`ss.tenant_id`, sql`ss.code`, section)}
    and (ss.grade = class_band(ss.tenant_id, ${section})
         or exists (select 1 from child_skill_state s join child c on c.id = s.child_id
                    where c.section = ${section} and c.active and s.rung_code = ss.rung_code
                      and s.skill_code = any(ss.registry_codes) and s.n_events > 0))`;

/** A severity's colour: the states of one severity share it (as `childTable` reads it). */
const severityColour = () => sql`select distinct on (severity) severity, colour from child_state order by severity, ord`;

/** Each signed-off answer once (`answer_placed`), on a reading not replaced, with the question it answered. */
const answers = (child: Fragment) => sql`
  select a.child_id, a.placed_rung, a.correct, a.observed_at, r.capture_id, r.working_shown, i.difficulty, d.ord as level_ord
  from answer_placed a
  join item_result r on r.id = a.item_result_id
  join capture c on c.id = r.capture_id and c.superseded_by is null
  join item i on i.id = r.item_id
  left join difficulty d on d.tenant_id = i.tenant_id and d.code = i.difficulty
  where a.confirmed_by is not null and ${child}`;

/** The three signals of the answers `a` (rule 5), as the report card counts them (`skillMap`). */
const signals = () => sql`
  count(*) filter (where a.correct)::int as right,
  count(*) filter (where a.correct = false and coalesce(a.working_shown, 'none') = 'none')::int as wrong,
  count(*) filter (where a.correct = false and coalesce(a.working_shown, 'none') <> 'none')::int as wrong_working,
  count(*) filter (where a.correct is null)::int as blank`;

export type TopicLine = {
  subject_code: string;
  subject: string;
  code: string;
  name: string;
  children: number;
  spread: Spread;
  /** The date of the newest signed-off answer of the class in the topic. */
  last: string | null;
};

/** A class's topics, subject by subject in the curriculum's order: each with its children counted by the state of their
 *  weakest skill in it, and the date it was last assessed. Only the topics of subjects the person may see in the class. */
export async function classTopics(section: string, me: Who): Promise<TopicLine[]> {
  return sql<TopicLine[]>`
    with sk as (${classSkills(section)}),
    kids as (select id from child where active and section = ${section}),
    per as (
      select s.child_id, sk.topic_code, min(cs.severity) as sev
      from child_skill_state s join kids k on k.id = s.child_id
      join sk on sk.tenant_id = s.tenant_id and sk.rung_code = s.rung_code and s.skill_code = any(sk.registry_codes)
      join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
      where s.n_events > 0 group by 1, 2),
    sv as (${severityColour()}),
    spread as (
      select per.topic_code, sv.colour, count(*)::int as n from per join sv on sv.severity = per.sev group by 1, 2),
    seen as (
      select sk.topic_code, max(a.observed_at)::date::text as last
      from (${answers(sql`a.child_id in (select id from kids)`)}) a join sk on sk.rung_code = a.placed_rung group by 1)
    select t.subject_code, coalesce(sb.label, sb.name) as subject, t.code, t.name,
           (select count(*)::int from kids) as children,
           coalesce((select jsonb_object_agg(colour, n) from spread where spread.topic_code = t.code), '{}'::jsonb) as spread,
           seen.last
    from topic t
    join subject sb on sb.tenant_id = t.tenant_id and sb.code = t.subject_code
    left join seen on seen.topic_code = t.code
    where exists (select 1 from sk where sk.topic_code = t.code) and ${seesClassIn(me, sql`${section}::text`, sql`t.subject_code`)}
    order by t.ord, t.code`.then((rows) => rows.map((r) => ({ ...r, spread: spreadOf(r.spread, r.children) })));
}

/** The counts as the rows gave them, with every colour present and the children with no state counted as `none`. */
function spreadOf(got: Partial<Spread>, children: number): Spread {
  const s: Spread = { red: got.red ?? 0, amber: got.amber ?? 0, green: got.green ?? 0, grey: got.grey ?? 0, none: 0 };
  s.none = Math.max(0, children - s.red - s.amber - s.green - s.grey);
  return s;
}

export type SkillLine = {
  code: string;
  name: string;
  children: number;
  spread: Spread;
  /** How many children are at each level: the level of the newest question on it each answered, the school's order. */
  levels: { level: string; n: number }[];
  last: string | null;
};

/** One topic of a class opened: its skills easy to hard, each with the children counted by their state on it and by
 *  the level they last answered at. */
export async function topicSkills(section: string, topic: string): Promise<SkillLine[]> {
  const rows = await sql<(SkillLine & { spread: Partial<Spread> })[]>`
    with sk as (select * from (${classSkills(section)}) x where x.topic_code = ${topic}),
    kids as (select id from child where active and section = ${section}),
    per as (
      select s.child_id, sk.code, min(cs.severity) as sev
      from child_skill_state s join kids k on k.id = s.child_id
      join sk on sk.tenant_id = s.tenant_id and sk.rung_code = s.rung_code and s.skill_code = any(sk.registry_codes)
      join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
      where s.n_events > 0 group by 1, 2),
    sv as (${severityColour()}),
    spread as (select per.code, sv.colour, count(*)::int as n from per join sv on sv.severity = per.sev group by 1, 2),
    a as (select a.*, sk.code from (${answers(sql`a.child_id in (select id from kids)`)}) a join sk on sk.rung_code = a.placed_rung),
    lvl as (
      select distinct on (child_id, code) child_id, code, difficulty, level_ord from a
      where difficulty is not null order by child_id, code, observed_at desc, level_ord desc nulls last),
    levels as (select code, level_ord, difficulty, count(*)::int as n from lvl group by 1, 2, 3)
    select sk.code, sk.name, (select count(*)::int from kids) as children,
           coalesce((select jsonb_object_agg(colour, n) from spread where spread.code = sk.code), '{}'::jsonb) as spread,
           coalesce((select jsonb_agg(jsonb_build_object('level', difficulty, 'n', n) order by level_ord) from levels
                      where levels.code = sk.code), '[]'::jsonb) as levels,
           (select max(observed_at)::date::text from a where a.code = sk.code) as last
    from sk order by sk.ladder_order nulls last, sk.code`;
  return rows.map((r) => ({ ...r, spread: spreadOf(r.spread, r.children) }));
}

export type ChildOnSkill = Signals & {
  id: string;
  roll_no: string;
  first_name: string;
  /** Their state on the skill (the weakest of its skills), none while they have no checked answer on it. */
  state: string | null;
  /** The level of the newest question on it they answered. */
  level: string | null;
  last: string | null;
  /** Their answers still waiting for a person, on papers this person sees: what their own page lists to check. */
  waiting: number;
};

/** One skill of a class opened: its children, those who need the educator first, a page of `size` at a time, each name
 *  read through pii.read_child, which logs who asked. → the page's children and how many there are in all. */
export async function skillChildren(section: string, skill: string, me: Who & { email: string }, page: number, size: number): Promise<{ rows: ChildOnSkill[]; of: number }> {
  const rows = await sql<(ChildOnSkill & { total: number })[]>`
    with ss as (select tenant_id, code, rung_code, registry_codes from skill where code = ${skill}),
    st as (
      select s.child_id, (array_agg(s.state order by cs.severity, cs.ord))[1] as state, min(cs.severity) as sev
      from child_skill_state s join ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code and s.skill_code = any(ss.registry_codes)
      join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
      join child c on c.id = s.child_id and c.section = ${section} and c.active
      where s.n_events > 0 group by 1),
    a as (select a.* from (${answers(sql`a.child_id in (select id from child where active and section = ${section})`)}) a
          join ss on ss.rung_code = a.placed_rung),
    sig as (select a.child_id, ${signals()}, max(a.observed_at)::date::text as last,
                   (array_agg(a.difficulty order by a.observed_at desc, a.level_ord desc nulls last)
                      filter (where a.difficulty is not null))[1] as level
            from a group by 1),
    x as (
      select c.id, c.roll_no, st.state, sig.level, sig.last,
             coalesce(sig.right, 0) as right, coalesce(sig.wrong, 0) as wrong,
             coalesce(sig.wrong_working, 0) as wrong_working, coalesce(sig.blank, 0) as blank,
             count(*) over ()::int as total, coalesce(st.sev, 99) as sev
      from child c left join st on st.child_id = c.id left join sig on sig.child_id = c.id
      where c.active and c.section = ${section}
      order by coalesce(st.sev, 99), roll_order(c.roll_no), c.roll_no
      limit ${size} offset ${(Math.max(1, page) - 1) * size})
    select x.*, p.first_name,
           (select count(*)::int from item_result r join capture k on k.id = r.capture_id
              join sheet_instance si on si.id = k.sheet_instance_id
             where si.child_id = x.id and r.state = 'candidate' and k.superseded_by is null and ${seesSheet(me, sql`si.id`)}) as waiting
    from x, lateral pii.read_child(x.id, ${me.email}) p
    order by x.sev, roll_order(x.roll_no), x.roll_no`;
  return { rows, of: rows[0]?.total ?? 0 };
}

export type PaperKind = { kind: string | null; papers: number; sets: number; children: number; most: number; last: string | null };

/** The papers of one topic a class's children answered, by kind (Nimish, 24 Oct 2026: "skills, then baseline
 *  assessment, then home assessments (some children get more), then practice"): how many papers, how many different
 *  ones, for how many children, the most any child had. Only papers the person sees (`staff_sees`). */
export async function topicPapers(section: string, topic: string, me: Who): Promise<PaperKind[]> {
  return sql<PaperKind[]>`
    with sk as (select * from (${classSkills(section)}) x where x.topic_code = ${topic}),
    p as (
      select distinct si.id, si.kind, si.sheet_template_id, si.child_id, a.observed_at
      from (${answers(sql`a.child_id in (select id from child where active and section = ${section})`)}) a
      join sk on sk.rung_code = a.placed_rung
      join capture c on c.id = a.capture_id join sheet_instance si on si.id = c.sheet_instance_id
      where ${seesSheet(me, sql`si.id`)}),
    each as (select kind, child_id, count(distinct id)::int as n from p group by 1, 2)
    select p.kind, count(distinct p.id)::int as papers, count(distinct p.sheet_template_id)::int as sets,
           count(distinct p.child_id)::int as children,
           (select max(n) from each where each.kind is not distinct from p.kind)::int as most,
           max(p.observed_at)::date::text as last
    from p group by p.kind`;
}

export type TopicPaper = Signals & {
  capture_id: string;
  qr_code: string;
  kind: string | null;
  title: string;
  date: string | null;
  topic_code: string;
  /** The pages of the scan its answers were read from, in order: what "See the child's page" opens. */
  pages: number[];
};

/** A child's papers topic by topic, newest first: each paper's signed-off answers on the topic in the three signals, and
 *  the pages of the scan they were read from. Only papers the person sees. */
export async function childTopicPapers(id: string, me: Who): Promise<TopicPaper[]> {
  return sql<TopicPaper[]>`
    with a as (${answers(sql`a.child_id = ${id}::uuid`)})
    select a.capture_id, si.qr_code, si.kind, ${paperName("t")} as title, max(a.observed_at)::date::text as date,
           ss.topic_code, ${signals()},
           (select array_agg(distinct coalesce((r.raw_read::jsonb ->> 'file_page')::int, (r.raw_read::jsonb ->> 'page')::int, 1))
              from item_result r where r.capture_id = a.capture_id) as pages
    from a
    join skill ss on ss.rung_code = a.placed_rung
    join capture c on c.id = a.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    where ${seesSheet(me, sql`si.id`)}
    group by a.capture_id, si.qr_code, si.kind, t.id, ss.topic_code
    order by max(a.observed_at) desc, si.qr_code`;
}

/** The level of the newest question a child answered on each skill (ties: the harder), with when. */
export async function childLevels(id: string): Promise<{ code: string; topic_code: string; level: string; at: string; ord: number }[]> {
  return sql<{ code: string; topic_code: string; level: string; at: string; ord: number }[]>`
    select distinct on (ss.code) ss.code, ss.topic_code, a.difficulty as level, a.observed_at::text as at, a.level_ord as ord
    from (${answers(sql`a.child_id = ${id}::uuid`)}) a join skill ss on ss.rung_code = a.placed_rung
    where a.difficulty is not null
    order by ss.code, a.observed_at desc, a.level_ord desc nulls last`;
}
