// One skill as a teacher reads it: a real question from the bank at each level, the kinds of
// question that test it with one of each, and the mistakes its questions are built to catch.
import { sql } from "./db";
import { itemColumns, type ItemRow } from "./queries-bank";

const inSkill = (code: string) => sql`i.skill_set_code = ${code} and i.status = 'active' and i.source = 'generated'`;

// The first question of each level by its key — the same one every time the page is opened, so a
// teacher who points at "the Hard example" means the one the next person sees.
export async function levelExamples(code: string): Promise<ItemRow[]> {
  return sql<ItemRow[]>`
    select distinct on (i.difficulty) ${itemColumns()} from item i
    where ${inSkill(code)} order by i.difficulty, i.item_key`;
}

export type KindRow = ItemRow & { n: number };

export async function skillKinds(code: string): Promise<KindRow[]> {
  return sql<KindRow[]>`
    select distinct on (i.fmt) ${itemColumns()}, count(*) over (partition by i.fmt)::int as n from item i
    where ${inSkill(code)} order by i.fmt, i.item_key`;
}

// How many of this skill's questions have a wrong answer that names each mistake — the mistakes the
// skill is most built to notice come first.
export async function skillMistakes(code: string): Promise<{ code: string; n: number }[]> {
  return sql<{ code: string; n: number }[]>`
    select m.code, count(distinct i.id)::int as n
    from item i, jsonb_array_elements(i.responses) r,
         jsonb_object_keys(coalesce(r -> 'misconceptions', '{}'::jsonb)) m(code)
    where ${inSkill(code)}
    group by m.code order by n desc, m.code`;
}

/** The ways a skill's levels are asked, from the tables that say so (`skill_level_question_type`), not from questions in
 *  the bank: a subject whose questions are not drawn from a bank (English, E0) has none there. Each with its words,
 *  whether a person checks every answer, and who approved it and when (one approval covers every skill that uses it). */
export type WaysRow = {
  code: string;
  words: string;
  levels: string[];
  open: boolean;
  by: string | null;
  at: string | null;
  /** the levels where an educator stopped it: no new paper draws it there (goals/gen_retire_a_kind.yaml) */
  stopped: string[];
};

export async function skillWays(code: string): Promise<WaysRow[]> {
  return sql<WaysRow[]>`
    select q.code, q.words, array_agg(l.difficulty order by d.ord) as levels,
           'open_response' = any(q.marked) as open, a.approved_by as by, a.approved_at as at,
           coalesce(array_agg(l.difficulty order by d.ord) filter (where k.stopped), '{}') as stopped
    from skill_level_question_type l
    join question_type q on q.tenant_id = l.tenant_id and q.code = l.question_type
    join difficulty d on d.tenant_id = l.tenant_id and d.code = l.difficulty
    left join question_type_approval a on a.tenant_id = q.tenant_id and a.question_type = q.code
    left join kind_stopped k on k.tenant_id = l.tenant_id and k.skill_code = l.skill_code
      and k.difficulty = l.difficulty and k.question_type = l.question_type
    where l.skill_code = ${code}
    group by q.code, q.words, q.marked, a.approved_by, a.approved_at
    order by min(d.ord), q.code`;
}

/** The mistakes a skill watches for, in words, from `skill_mistake`: what a child writes and why. */
export async function skillWatches(code: string): Promise<{ code: string; name: string; description: string }[]> {
  return sql<{ code: string; name: string; description: string }[]>`
    select distinct on (m.code) m.code, m.name, m.description
    from skill_mistake k join misconception m on m.tenant_id = k.tenant_id and m.code = k.misconception_code and m.op = k.op
    where k.skill_code = ${code} order by m.code`;
}

/** An English sample as an approver reads it (goals/smp_skill_shows_its_samples.yaml): the question as printed, the right
 *  answer, and each likely wrong answer with the mistake it names in words; for a kind a person reads every answer of,
 *  what a right answer says and the rubric. As it stands now (`english_sample_now`): an educator's newest edit where
 *  there is one, with who made it and when (goals/edt_edit_samples_and_kinds.yaml), else the seed's. */
export type SampleRow = {
  difficulty: string;
  kind: string;
  kind_words: string;
  open: boolean;
  ord: number;
  ask: string;
  text: string | null;
  options: string[] | { left: string[]; right: string[] } | null;
  answer: string | string[] | string[][] | Record<string, string | string[]>;
  accept: string[];
  key_points: string[] | null;
  not_words: string[] | null;
  passage_code: string | null;
  rubric_code: string | null;
  passage: { title: string; text: string } | null;
  rubric: { name: string; scale: string[]; criteria: { code: string; name: string; levels: Record<string, string> }[] } | null;
  wrong: { answer: string; mistake_code: string; mistake: string; description: string | null }[];
  edited_by: string | null;
  /** the number of the sample it was made from (goals/gen_from_a_sample.yaml); none when a person wrote it */
  made_from: number | null;
  edited_at: string | null;
  earlier: number;
};

export async function skillSamples(code: string): Promise<SampleRow[]> {
  return sql<SampleRow[]>`
    select e.difficulty, e.question_type as kind, q.words as kind_words, 'open_response' = any(q.marked) as open, e.ord,
           e.ask, e.text, e.options, e.answer, e.accept, e.key_points, e.not_words, e.passage_code, e.rubric_code,
           case when p.code is null then null else jsonb_build_object('title', p.title, 'text', p.text) end as passage,
           case when r.code is null then null
                else jsonb_build_object('name', r.name, 'scale', r.scale, 'criteria', r.criteria) end as rubric,
           coalesce((select jsonb_agg(jsonb_build_object('answer', w ->> 'answer', 'mistake_code', m.code,
                                                         'mistake', m.name, 'description', m.description)
                                      order by w ->> 'answer')
                     from jsonb_array_elements(e.wrong) w
                     join misconception m on m.tenant_id = e.tenant_id and m.code = w ->> 'mistake_code' and m.op = 'any'),
                    '[]'::jsonb) as wrong,
           e.edited_by, e.edited_at, e.earlier::int as earlier, e.made_from
    from english_sample_now e
    join question_type q on q.tenant_id = e.tenant_id and q.code = e.question_type
    join skill_level_question_type l on l.tenant_id = e.tenant_id and l.skill_code = e.skill_code
      and l.difficulty = e.difficulty and l.question_type = e.question_type
    left join passage p on p.tenant_id = e.tenant_id and p.code = e.passage_code
    left join rubric r on r.tenant_id = e.tenant_id and r.code = e.rubric_code
    where e.skill_code = ${code}
    order by e.difficulty, l.place nulls last, e.question_type, e.ord`;
}

/** What an educator picks from when changing a skill's samples (goals/edt_edit_samples_and_kinds.yaml): the passages
 *  of its grade, the rubrics it may be read against, its mistakes, and the approved kinds a level may ask. */
export type SampleChoices = {
  /** samples a level keeps of each kind it asks (the `samples.per_kind` threshold row) */
  few: number;
  /** the most questions asked for at once from one sample (the `generate.max_per_request` row) */
  most: number;
  passages: { code: string; title: string }[];
  rubrics: { code: string; name: string }[];
  mistakes: { code: string; name: string }[];
  kinds: { code: string; words: string; open: boolean }[];
};

export async function sampleChoices(code: string): Promise<SampleChoices> {
  const [[few], passages, rubrics, mistakes, kinds] = await Promise.all([
    sql<{ n: number; most: number }[]>`
      select coalesce((select value::int from threshold where key = 'samples.per_kind'), 3) as n,
             coalesce((select value::int from threshold where key = 'generate.max_per_request'), 20) as most`,
    sql<{ code: string; title: string }[]>`
      select p.code, p.title from passage p join skill s on s.tenant_id = p.tenant_id and s.grade = p.grade
      where s.code = ${code} order by p.title, p.code`,
    sql<{ code: string; name: string }[]>`
      select r.code, r.name from rubric r where ${code} = any(r.skill_codes) order by r.name`,
    sql<{ code: string; name: string }[]>`
      select distinct on (m.code) m.code, m.name
      from skill_mistake k join misconception m on m.tenant_id = k.tenant_id and m.code = k.misconception_code and m.op = k.op
      where k.skill_code = ${code} order by m.code`,
    // the one list the engine accepts from too (`level_kind_choice`), for the skill's own subject
    sql<{ code: string; words: string; open: boolean }[]>`
      select k.code, k.words, k.open from level_kind_choice k
      where k.subject_code = (select t.subject_code from skill s join topic t on t.tenant_id = s.tenant_id
                                and t.code = s.topic_code where s.code = ${code})
      order by k.words`,
  ]);
  return { few: few.n, most: few.most, passages, rubrics, mistakes, kinds };
}

/** How many samples a level holds of a kind as they stand, linked to the level or not: a kind added needs three. */
export async function sampleCount(code: string, level: string, kind: string): Promise<number> {
  const [r] = await sql<{ n: number }[]>`
    select count(*)::int as n from english_sample_now
    where skill_code = ${code} and difficulty = ${level} and question_type = ${kind}`;
  return r?.n ?? 0;
}

/** The database's time as a page is drawn: an approval form carries it, and lands only on skills none of whose samples
 *  or kinds changed after it (goals/edt_edit_samples_and_kinds.yaml). Text, since postgres.js keeps a time to the
 *  millisecond and a change stamped in the same millisecond would then look older than the page. */
export async function openedAt(): Promise<string> {
  const [r] = await sql<{ at: string }[]>`select now()::text as at`;
  return r.at;
}
