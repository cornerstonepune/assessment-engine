import { sql } from "./db";
import { inScope, type Scope } from "./scope";

// Whether a topic has been taught is said for each class (goals/f1f-taught-per-class.yaml, ADR 0073 D5). The one rule
// is the database's `taught_in(tenant, topic, class)`: the class's own word, else the school's switch. A page about a
// class or a child asks it of that class; a list for the school, or for an educator's classes, asks it of each and
// counts a topic taught where any one of them has been taught it.

type Fragment = ReturnType<typeof sql>;

/** Taught in this class. `tenant` and `topic` are the row's own columns. */
export const taughtIn = (tenant: Fragment, topic: Fragment, section: Fragment | string) =>
  sql`taught_in(${tenant}, ${topic}, ${section})`;

/** Taught in any class the scope shows: an educator's own, or every class with a child on the roll. */
export const taughtFor = (scope: Scope, tenant: Fragment, topic: Fragment) =>
  scope.classes
    ? sql`exists (select 1 from unnest(${scope.classes}::text[]) as k(section) where taught_in(${tenant}, ${topic}, k.section))`
    : sql`exists (select 1 from child k where k.tenant_id = ${tenant} and k.active and taught_in(${tenant}, ${topic}, k.section))`;

/** The classes a scope shows, in order: an educator's own, or every class with a child on the roll. */
export async function classesOf(scope: Scope): Promise<string[]> {
  if (scope.classes) return [...scope.classes].sort();
  const rows = await sql<{ section: string }[]>`select distinct section from child where active order by section`;
  return rows.map((r) => r.section);
}

/** Whether a topic is taught in a grade: in any class of that grade the scope shows. A grade none of whose classes the
 *  scope shows follows the school's switch, as a class no one has spoken for does. */
export async function taughtByGrade(scope: Scope): Promise<(band: string, topic: string | null) => boolean> {
  const [rows, school] = await Promise.all([
    sql<{ band: string; topic: string; taught: boolean }[]>`
      select k.band, t.code as topic, bool_or(taught_in(t.tenant_id, t.code, k.section)) as taught
      from topic t
      cross join (select distinct section, band from child where active and ${inScope(scope, sql`section`)}) k
      group by 1, 2`,
    sql<{ code: string; taught: boolean }[]>`select code, taught_in(tenant_id, code, null) as taught from topic`,
  ]);
  const by = new Map(rows.map((r) => [`${r.band}|${r.topic}`, r.taught]));
  const own = new Map(school.map((t) => [t.code, t.taught]));
  return (band, topic) => by.get(`${band}|${topic}`) ?? own.get(topic ?? "") ?? false;
}
