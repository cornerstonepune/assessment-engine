import type { Grades } from "./queries";

// The words a class and a count are said in, shared by the pages that list classes. (What waits on a person was Today's
// list here; it is now one list of tasks, lib/todo.ts, goals/nav_teacher_scope_and_todo.yaml.)

/** "Grade 2 · 2B": a class as an educator says it. */
export const classWords = (g: Grades, band: string, section: string) => `${g.name(band)} · ${section}`;
/** A count and its noun, said as a person says it: 1 child, 2 children. */
export const many = (n: number, one: string, more = `${one}s`) => `${n} ${n === 1 ? one : more}`;
