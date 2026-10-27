import { sql } from "./db";
import { mayUse } from "./access";
import type { Session } from "./auth";

// Which classes a page shows the signed-in person (goals/f1b-my-classes-first.yaml, ADR 0073). Nimish, 2026-10-14:
// "Then the teachers only see, when Achal logs in, things that are relevant to his grades." An educator sees the classes
// on their staff entry; the coordinator sees every class; an educator linked to no class yet sees every class, told why,
// rather than an empty site.

/** `classes` null is every class. */
export type Scope = { classes: string[] | null; note: string | null };

export const EVERY_CLASS: Scope = { classes: null, note: null };

/** The classes a page shows the person: their own (`ownClasses`), or every class for a person with none. A default each page
 *  narrows with its own filters, never what they may reach: that is `reachOf` (goals/ux9c-one-role.yaml). */
export const scopeOf = (me: Pick<Session, "role" | "classes">): Scope => ownClasses(me);

/** The classes whose pages, papers and decisions a person may open and take: every class, for every member of staff for
 *  now (`mayUse`, goals/ux9c-one-role.yaml); their own once the roles split again. */
export function reachOf(me: Pick<Session, "role" | "classes">): Scope {
  return mayUse(me, "every_class") ? EVERY_CLASS : ownClasses(me);
}

/** The classes a person teaches: what a page opens on first, its grade (`gradesOf`), never what it hides. A person
 *  linked to no class (the coordinator, so far) opens on every class. */
export function ownClasses(me: Pick<Session, "role" | "classes">): Scope {
  return me.classes?.length ? { classes: me.classes, note: null } : EVERY_CLASS;
}

/** The grades of the person's own classes, in the school's order (`class_band`, the one rule): what Curriculum, the bank
 *  and the worksheets open on (goals/ux6-curriculum-for-the-educator.yaml). None for every class: the coordinator's
 *  pages, and those of an educator linked to no class, open on no one grade. */
export async function gradesOf(scope: Scope): Promise<string[]> {
  if (!scope.classes) return [];
  const rows = await sql<{ band: string }[]>`
    select distinct class_band(tenant_id, section) as band, grade_ord(tenant_id, class_band(tenant_id, section)) as ord
    from child where active and section = any(${scope.classes}) order by 2`;
  return rows.map((r) => r.band);
}

/** A where-clause piece: the class in `section` is one of the scope's (always true for every class). */
export const inScope = (scope: Scope, section: ReturnType<typeof sql>) =>
  scope.classes ? sql`${section} = any(${scope.classes})` : sql`true`;

/** Whether a class is one the person sees: a page for another class shows nothing of it. */
export const isMine = (scope: Scope, section: string | null | undefined) =>
  !scope.classes || (section != null && scope.classes.includes(section));

/** A child's class, read before anything of the child is (their name is read through the logged accessor only once the
 *  page is theirs to see); null for no such child. */
export async function childSection(id: string): Promise<string | null> {
  const [r] = await sql<{ section: string }[]>`select section from child where id = ${id}::uuid`;
  return r?.section ?? null;
}

/** A paper's class — its own, or its child's — by its id or its printed code; null for no such paper. */
export async function paperSection(by: { id: string } | { qr: string }): Promise<string | null> {
  const [r] = await sql<{ section: string | null }[]>`
    select coalesce(si.section, ch.section) as section from sheet_instance si left join child ch on ch.id = si.child_id
    where ${"id" in by ? sql`si.id = ${by.id}::uuid` : sql`si.qr_code = ${by.qr}`}`;
  return r?.section ?? null;
}

/** The class of the paper a scan was read as; null for a scan not yet sorted onto any paper, which has no class. */
export async function captureSection(id: string): Promise<string | null> {
  const [r] = await sql<{ section: string | null }[]>`
    select coalesce(si.section, ch.section) as section from capture c
    left join sheet_instance si on si.id = c.sheet_instance_id left join child ch on ch.id = si.child_id
    where c.id = ${id}::uuid`;
  return r?.section ?? null;
}

/** The answer an image route gives for another class's child or paper. */
export const notYoursResponse = () => new Response("not one of your classes", { status: 403 });

/** The class of the paper an answer was read on; null for no such answer. */
export async function resultSection(id: string): Promise<string | null> {
  const [r] = await sql<{ section: string | null }[]>`
    select coalesce(si.section, ch.section) as section from item_result r
    join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id
    left join child ch on ch.id = si.child_id
    where r.id = ${id}::uuid`;
  return r?.section ?? null;
}

/** The class of the child a planned paper is for; null for no such plan. */
export async function prescriptionSection(id: string): Promise<string | null> {
  const [r] = await sql<{ section: string }[]>`
    select c.section from prescription p join child c on c.id = p.child_id where p.id = ${id}::uuid`;
  return r?.section ?? null;
}

/** The classes of the children named; a child not found counts as no one's class (null). */
export async function childrenSections(ids: string[]): Promise<(string | null)[]> {
  if (!ids.length) return [];
  const rows = await sql<{ id: string; section: string }[]>`select id::text, section from child where id = any(${ids}::uuid[])`;
  const of = new Map(rows.map((r) => [r.id, r.section]));
  return ids.map((id) => of.get(id) ?? null);
}
