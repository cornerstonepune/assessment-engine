import { sql } from "./db";
import { EVERY_CLASS, type Scope } from "./scope";
import { classesOf, taughtFor } from "./taught";

// What waits on a person, and who it is for (goals/ny1-needs-you.yaml): who decides each kind of thing (`people.decides`,
// by the staff list's roles), which topics are taught and who said so, and the questions the engine drafted for a
// person to answer (`ask`).

export const ROLE_WORDS: Record<string, string> = { coordinator: "a coordinator", educator: "an educator", specialist: "a specialist" };

/** A class's word on a topic (goals/f1f-taught-per-class.yaml): its own (`own`), or the school's switch while no one
 *  has spoken for the class — with who said it, if a person did, and when. */
export type ClassTaught = { section: string; taught: boolean; by: string | null; at: string | null; own: boolean };

/** `taught`: in any of the classes shown. */
export type Topic = { code: string; name: string; taught: boolean; classes: ClassTaught[]; skills: string[] };

/** Every topic in the tree's order, with its skills' names and each class's word on it: the classes of the scope. */
export async function topics(scope: Scope = EVERY_CLASS): Promise<Topic[]> {
  const classes = await classesOf(scope);
  const rows = await sql<Omit<Topic, "taught">[]>`
    select t.code, t.name,
           coalesce(array_agg(s.name order by s.code) filter (where s.code is not null), '{}') as skills,
           (select coalesce(json_agg(json_build_object(
                      'section', k.section, 'taught', taught_in(t.tenant_id, t.code, k.section),
                      'by', coalesce(ct.taught_by, t.taught_by), 'at', coalesce(ct.taught_at, t.taught_at)::text,
                      'own', ct.section is not null) order by k.section), '[]')
            from unnest(${classes}::text[]) as k(section)
            left join class_topic ct on ct.tenant_id = t.tenant_id and ct.topic_code = t.code and ct.section = k.section)
             as classes
    from topic t left join skill_set s on s.tenant_id = t.tenant_id and s.topic_code = t.code
    group by t.tenant_id, t.code, t.name, t.taught_by, t.taught_at, t.ord
    order by t.ord`;
  return rows.map((t) => ({ ...t, taught: t.classes.some((c) => c.taught) }));
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

/** Topics no class of the scope has been taught yet, as Curriculum lists them to say so. */
export async function topicsOff(scope: Scope = EVERY_CLASS): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from topic t where not ${taughtFor(scope, sql`t.tenant_id`, sql`t.code`)}`;
  return n;
}
