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
