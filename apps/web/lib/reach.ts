import { cache } from "react";
import { sql } from "./db";
import type { Session } from "./auth";
import { EVERY_CLASS, ownClasses, type Scope } from "./scope";

// Who may see and act on a child's answers, papers, scans and the counts of them (goals/own_who_sees_answers.yaml).
// Nimish, 27 Oct 2026: "their assessments, answers to be checked etc. should be restricted to their grade ... Achal should
// only see the papers he has uploaded." The rule is the database's one function, `staff_sees` (migration
// 20261220090000): a coordinator sees everything; an educator, what they put in, or what is of a class on their staff
// entry in a subject on it. This file holds no rule: it hands the signed-in person to that function, for lists (a
// where-clause piece), for one thing a link or a form names (`sees`), and for the classes it allows (`reachOf`).
// Curriculum, skills, the question bank and the skill pages are not asked: they are every educator's.

export type Who = Pick<Session, "role" | "classes" | "subjects" | "id">;

const who = (me: Who) =>
  sql`${me.role}, ${me.classes ?? []}::text[], ${me.subjects ?? []}::text[], ${me.id ?? null}::uuid`;

/** A where-clause piece: the person may see the printed copy whose id is `sheet`. */
export const seesSheet = (me: Who, sheet: ReturnType<typeof sql>) => sql`staff_sees_sheet(${who(me)}, ${sheet})`;

/** A where-clause piece: the person may see the scan whose id is `capture`. */
export const seesCapture = (me: Who, capture: ReturnType<typeof sql>) => sql`staff_sees_capture(${who(me)}, ${capture})`;

/** A where-clause piece: the person may see what is of the class in `section` (a child, a class's work). */
export const seesClass = (me: Who, section: ReturnType<typeof sql>) => sql`staff_sees(${who(me)}, ${section}, null, null)`;

/** A where-clause piece: the person sees what was put in by `uploadedBy` (their own, or everything). */
export const seesUploader = (me: Who, uploadedBy: ReturnType<typeof sql>) => sql`staff_sees(${who(me)}, null, null, ${uploadedBy})`;

/** A where-clause piece on a `flow_run` row `r`: a file sent to be read, seen by whoever put it in, and by whoever sees
 *  a paper read from it. */
export const seesRun = (me: Who, r: ReturnType<typeof sql>) => sql`(
  staff_sees(${who(me)}, null, null, ${r}.uploaded_by)
  or exists (select 1 from jsonb_array_elements(coalesce(${r}.result -> 'copies', '[]'::jsonb)) k
             where k ->> 'capture_id' is not null and staff_sees_capture(${who(me)}, (k ->> 'capture_id')::uuid)))`;

/** The classes whose children and class work a person may see: every class (null) where the rule says so (asked of no
 *  class at all), else those of the school's classes it allows. Once per request. */
export const reachOf = cache(async (me: Who): Promise<Scope> => {
  const [r] = await sql<{ every: boolean; classes: string[] }[]>`
    select staff_sees(${who(me)}, null, null, null) as every,
           coalesce(array_agg(distinct section order by section) filter (where staff_sees(${who(me)}, section, null, null)), '{}') as classes
    from child where active`;
  return r?.every ? EVERY_CLASS : { classes: r?.classes ?? [], note: null };
});

/** The classes a page of class work (results, children, papers to make, reports) opens on: the person's own classes,
 *  each one the rule lets them see, or every class it lets them see for a person linked to none. Never wider than
 *  `reachOf`: an educator linked to no class is not shown every class. */
export async function workScope(me: Who): Promise<Scope> {
  const [reach, own] = [await reachOf(me), ownClasses(me)];
  if (!own.classes) return reach;
  if (!reach.classes) return own;
  return { classes: own.classes.filter((c) => reach.classes!.includes(c)), note: null };
}

/** One thing a link or a form names: a printed copy (by its id or its code), a scan, an answer, a child, a file sent to be
 *  read (`run`, seen by whoever put it in) or a class. */
export type Thing =
  | { sheet: string }
  | { qr: string }
  | { capture: string }
  | { result: string }
  | { child: string }
  | { run: string }
  | { section: string | null };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function asked(me: Who, t: Thing) {
  if ("section" in t) return sql`staff_sees(${who(me)}, ${t.section}, null, null)`;
  if ("qr" in t) return sql`(select staff_sees_sheet(${who(me)}, id) from sheet_instance where qr_code = ${t.qr} limit 1)`;
  const id = Object.values(t)[0] as string;
  if (!UUID.test(id)) return sql`false`;
  if ("sheet" in t) return sql`staff_sees_sheet(${who(me)}, ${id}::uuid)`;
  if ("capture" in t) return sql`staff_sees_capture(${who(me)}, ${id}::uuid)`;
  if ("run" in t) return sql`(select ${seesRun(me, sql`r`)} from flow_run r where r.id = ${id}::uuid)`;
  if ("result" in t) return sql`(select staff_sees_capture(${who(me)}, capture_id) from item_result where id = ${id}::uuid)`;
  return sql`(select staff_sees(${who(me)}, section, null, null) from child where id = ${id}::uuid)`;
}

/** Whether the person may see every thing named; a thing not found is no one's. */
export async function sees(me: Who, things: Thing[]): Promise<boolean> {
  for (const t of things) {
    const [r] = await sql<{ ok: boolean | null }[]>`select ${asked(me, t)} as ok`;
    if (!r?.ok) return false;
  }
  return true;
}
