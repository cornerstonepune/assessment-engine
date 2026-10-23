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
};

export async function skillWays(code: string): Promise<WaysRow[]> {
  return sql<WaysRow[]>`
    select q.code, q.words, array_agg(l.difficulty order by d.ord) as levels,
           'open_response' = any(q.marked) as open, a.approved_by as by, a.approved_at as at
    from skill_level_question_type l
    join question_type q on q.tenant_id = l.tenant_id and q.code = l.question_type
    join difficulty d on d.tenant_id = l.tenant_id and d.code = l.difficulty
    left join question_type_approval a on a.tenant_id = q.tenant_id and a.question_type = q.code
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
