import { notFound } from "next/navigation";
import type { Session } from "../auth";
import { type BodyOf, EngineDown, type PostPath, engineSend } from "../engine";
import type { Day, OnePeriod, Week } from "./types";

// What the K2 educator's screens read, all from the engine with her email as `actor` (M1-09): the engine finds her staff
// id and her classes. Behind `educator.timetable_enabled` (config, off): the engine refuses while it is off, and every
// page is then not found.
async function read<T, P extends PostPath = PostPath>(path: P, body: BodyOf<P>): Promise<T> {
  const res = await engineSend(path, body);
  if (res.status === 404 || res.status === 403) notFound(); // switched off, a class she does not hold, a day not on record
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}).`);
  return (await res.json()) as T;
}

/** Her day (M1-06's /timetable/day): her first class unless she picked one, today unless she picked a day. */
export const dayOf = (me: Pick<Session, "email">, q: { class_id?: string; day?: string }) => read<Day, "/timetable/day">("/timetable/day", { actor: me.email, ...q });

/** Her week, Monday to Saturday (M1-06's /timetable/week). */
export const weekOf = (me: Pick<Session, "email">, q: { class_id?: string; week_of?: string }) => read<Week, "/timetable/week">("/timetable/week", { actor: me.email, ...q });

/** One period of one day, with the planner's lines for its subject this fortnight (M1-06's /timetable/period). */
export const periodOf = (me: Pick<Session, "email">, q: { class_id?: string; day: string; period_id: string }) =>
  read<OnePeriod, "/timetable/period">("/timetable/period", { actor: me.email, ...q });
