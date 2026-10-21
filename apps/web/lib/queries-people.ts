import { sql } from "./db";
import { EVERY_CLASS, type Scope } from "./scope";
import { classesOf, taughtFor } from "./taught";

// What waits on a person, and who it is for (goals/ny1-needs-you.yaml): who decides each kind of thing (`people.decides`,
// by the staff list's roles), which topics are taught and who said so, and the questions the engine drafted for a
// person to answer (`ask`).

export const ROLE_WORDS: Record<string, string> = { coordinator: "a coordinator", educator: "an educator", specialist: "a specialist" };

/** A class's word on one skill (goals/t1-topics-are-operations.yaml): its own (`own`), or the school's while no one has
 *  spoken for the class — with who said it, if a person did, and when. `reaches`: one of its levels is the class's
 *  grade or below, so the class's children can be given it (a child never meets a grade above their own). */
export type SkillTaught = {
  code: string;
  name: string;
  taught: boolean;
  own: boolean;
  by: string | null;
  at: string | null;
  reaches: boolean;
};

/** A class's word on a topic: taught when any of its skills is (`taught_in`), each skill's own word beside it. `own`, `by`
 *  and `at` are the latest word said of one of its skills for the class, else the school's. */
export type ClassTaught = { section: string; taught: boolean; by: string | null; at: string | null; own: boolean; skills: SkillTaught[] };

/** `taught`: in any of the classes shown. `shown`: one of its skills is taught in one of them and reaches that class's
 *  grade, so a page about those classes can show it (goals/t1-topics-are-operations.yaml). */
export type Topic = { code: string; name: string; taught: boolean; shown: boolean; classes: ClassTaught[]; skills: string[] };

/** Every topic in the tree's order, with its skills' names and each class's word on each of its skills: the classes
 *  of the scope. */
export async function topics(scope: Scope = EVERY_CLASS): Promise<Topic[]> {
  const classes = await classesOf(scope);
  const rows = await sql<{ code: string; name: string; skills: string[]; classes: { section: string; skills: SkillTaught[] }[] }[]>`
    select t.code, t.name,
           coalesce((select array_agg(s.name order by s.code) from skill_set s
                     where s.tenant_id = t.tenant_id and s.topic_code = t.code), '{}') as skills,
           (select coalesce(json_agg(json_build_object('section', k.section, 'skills', (
                      select coalesce(json_agg(json_build_object(
                               'code', s.code, 'name', s.name, 'taught', skill_taught_in(s.tenant_id, s.code, k.section),
                               'own', cs.section is not null, 'by', coalesce(cs.taught_by, s.taught_by),
                               'at', coalesce(cs.taught_at, s.taught_at)::text,
                               'reaches', exists (select 1 from skill_level l where l.tenant_id = s.tenant_id and l.skill_code = s.code
                                                  and grade_ord(l.tenant_id, l.grade) <= grade_ord(s.tenant_id, k.band))
                             ) order by s.code), '[]')
                      from skill_set s
                      left join class_skill cs on cs.tenant_id = s.tenant_id and cs.skill_set_code = s.code
                                              and cs.section = k.section
                      where s.tenant_id = t.tenant_id and s.topic_code = t.code)) order by k.section), '[]')
            from (select c.section, class_band(t.tenant_id, c.section) as band
                  from unnest(${classes}::text[]) as c(section)) k) as classes
    from topic t
    order by t.ord`;
  return rows.map((t) => {
    const each: ClassTaught[] = t.classes.map((c) => {
      const said = c.skills.filter((s) => s.own).sort((a, b) => String(b.at).localeCompare(String(a.at)))[0];
      const school = c.skills.find((s) => s.by);
      return {
        section: c.section,
        taught: c.skills.some((s) => s.taught),
        own: Boolean(said),
        by: (said ?? school)?.by ?? null,
        at: (said ?? school)?.at ?? null,
        skills: c.skills,
      };
    });
    return {
      code: t.code,
      name: t.name,
      skills: t.skills,
      classes: each,
      taught: each.some((c) => c.taught),
      shown: each.some((c) => c.skills.some((s) => s.taught && s.reaches)),
    };
  });
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
