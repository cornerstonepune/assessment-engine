import { sql } from "./db";
import { inScope, type Scope } from "./scope";

// Whether a skill has been taught is said for each class (goals/f1f-taught-per-class.yaml), skill by skill
// (goals/t1-topics-are-operations.yaml). The one rule is the database's `skill_taught_in(tenant, skill, class)`: the
// class's own word, else the school's; a topic is taught in a class when any of its skills is (`taught_in`). A page
// about a class or a child asks it of that class; a list for the school, or for an educator's classes, asks it of each
// and counts a skill taught where any one of them has been taught it.

type Fragment = ReturnType<typeof sql>;

/** Taught in this class. `tenant` and `topic` are the row's own columns. */
export const taughtIn = (tenant: Fragment, topic: Fragment, section: Fragment | string) =>
  sql`taught_in(${tenant}, ${topic}, ${section})`;

/** Taught in any class the scope shows: an educator's own, or every class with a child on the roll. */
export const taughtFor = (scope: Scope, tenant: Fragment, topic: Fragment) =>
  scope.classes
    ? sql`exists (select 1 from unnest(${scope.classes}::text[]) as k(section) where taught_in(${tenant}, ${topic}, k.section))`
    : sql`exists (select 1 from child k where k.tenant_id = ${tenant} and k.active and taught_in(${tenant}, ${topic}, k.section))`;

/** This skill taught in this class. `tenant` and `skill` are the row's own columns. */
export const skillTaughtIn = (tenant: Fragment, skill: Fragment, section: Fragment | string) =>
  sql`skill_taught_in(${tenant}, ${skill}, ${section})`;

/** This skill taught in any class the scope shows: an educator's own, or every class with a child on the roll. */
export const skillTaughtFor = (scope: Scope, tenant: Fragment, skill: Fragment) =>
  scope.classes
    ? sql`exists (select 1 from unnest(${scope.classes}::text[]) as k(section) where skill_taught_in(${tenant}, ${skill}, k.section))`
    : sql`exists (select 1 from child k where k.tenant_id = ${tenant} and k.active and skill_taught_in(${tenant}, ${skill}, k.section))`;

/** The classes a scope shows, in order: an educator's own, or every class with a child on the roll. */
export async function classesOf(scope: Scope): Promise<string[]> {
  if (scope.classes) return [...scope.classes].sort();
  const rows = await sql<{ section: string }[]>`select distinct section from child where active order by section`;
  return rows.map((r) => r.section);
}

/** Whether a skill is taught in a grade: in any class of that grade the scope shows. A grade none of whose classes the
 *  scope shows follows the school's word, as a class no one has spoken for does. */
export async function taughtByGrade(scope: Scope): Promise<(band: string, skill: string) => boolean> {
  const [rows, school] = await Promise.all([
    sql<{ band: string; skill: string; taught: boolean }[]>`
      select k.band, s.code as skill, bool_or(skill_taught_in(s.tenant_id, s.code, k.section)) as taught
      from skill_set s
      cross join (select distinct section, band from child where active and ${inScope(scope, sql`section`)}) k
      group by 1, 2`,
    sql<{ code: string; taught: boolean }[]>`select code, skill_taught_in(tenant_id, code, null) as taught from skill_set`,
  ]);
  const by = new Map(rows.map((r) => [`${r.band}|${r.skill}`, r.taught]));
  const own = new Map(school.map((t) => [t.code, t.taught]));
  return (band, skill) => by.get(`${band}|${skill}`) ?? own.get(skill) ?? false;
}
