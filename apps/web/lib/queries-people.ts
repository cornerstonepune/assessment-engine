import { sql } from "./db";

// What waits on a person, and who it is for (goals/ny1-needs-you.yaml): who decides each kind of thing (`people.decides`,
// by the staff list's roles), which topics are taught and who said so, and the questions the engine drafted for a
// person to answer (`ask`).

export const ROLE_WORDS: Record<string, string> = { coordinator: "a coordinator", educator: "an educator", specialist: "a specialist" };

/** {kind of waiting: the roles whose it is}, as the row says. */
export async function decides(): Promise<Record<string, string[]>> {
  const [row] = await sql<{ value: Record<string, string[]> }[]>`select value from config where key = 'people.decides'`;
  return row?.value ?? {};
}

export type Topic = { code: string; name: string; taught: boolean; taught_by: string | null; taught_at: string | null; skills: string[] };

/** Every topic in the tree's order, whether it is taught and who said so, with its skills' names. */
export async function topics(): Promise<Topic[]> {
  return sql<Topic[]>`
    select t.code, t.name, t.taught, t.taught_by, t.taught_at::text as taught_at,
           coalesce(array_agg(s.name order by s.code) filter (where s.code is not null), '{}') as skills
    from topic t left join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    group by t.code, t.name, t.taught, t.taught_by, t.taught_at, t.ord
    order by t.ord`;
}

export type Ask = {
  code: string;
  for_role: string;
  question: string;
  drafted: string;
  why: string | null;
  source: string;
  link: string | null;
  answer: "agreed" | "corrected" | null;
  correction: string | null;
  answered_by: string | null;
  answered_at: string | null;
};

/** Every question drafted for a person, in the order drafted. */
export async function asks(): Promise<Ask[]> {
  return sql<Ask[]>`
    select code, for_role, question, drafted, why, source, link, answer, correction, answered_by,
           answered_at::text as answered_at
    from ask order by ord, code`;
}

/** {role: questions still waiting}, for Today. */
export async function asksWaiting(): Promise<{ for_role: string; n: number }[]> {
  return sql<{ for_role: string; n: number }[]>`
    select for_role, count(*)::int as n from ask where answer is null group by for_role order by for_role`;
}

/** Skills waiting for an approval, taught or not: one is approved before its topic is switched on. Today, Curriculum
 *  and the approval page all count these. */
export async function skillsWaiting(): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from skill_set where status <> 'ratified'`;
  return n;
}

/** Topics not taught yet, as Curriculum lists them to switch on. */
export async function topicsOff(): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from topic where not taught`;
  return n;
}
