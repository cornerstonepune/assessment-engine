import { notFound } from "next/navigation";
import type { Session } from "../auth";
import { type BodyOf, EngineDown, type PostPath, engineSend } from "../engine";
import type { ActivityPage, CatalogueItem, Day, MaterialsList, OnePeriod, SchoolList, WaitingNote, Week } from "./types";

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

/** Whether her screens are open to her (the switch on, or the staff preview): a screen that reads no timetable asks
 * first, so it is not found exactly when the timetable is not. */
export const openTo = (me: Pick<Session, "email">) => read<{ previewing: boolean }, "/timetable/open">("/timetable/open", { actor: me.email });

export type Span = "day" | "week" | "fortnight";
const DAYS: Record<Span, number> = { day: 0, week: 6, fortnight: 13 };
const until = (from: string, days: number) => new Date(Date.parse(`${from}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);

/** Her class's list from `from` for a day, a week or a fortnight (M1-10's /materials/build: the list for that range,
 * refreshed from the plan, never a second one), each day its own group. The staff preview is answered the list worked
 * out and not kept (D-076), so its answer is used as it comes, never read back by id. Null when the list is not hers. */
export async function materialsOf(me: Pick<Session, "email">, class_id: string, from: string, span: Span): Promise<MaterialsList | null> {
  const res = await engineSend("/materials/build", { actor: me.email, class_id, period: span, from, to: until(from, DAYS[span]), group_by: "day" });
  if (res.status === 403) return null;
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}).`);
  return (await res.json()) as MaterialsList;
}

/** The catalogue she adds from: a line is always a catalogue item, never free text (D-071). */
export const catalogueOf = async (me: Pick<Session, "email">) =>
  (await read<{ items: CatalogueItem[] }, "/materials/catalogue/list">("/materials/catalogue/list", { actor: me.email })).items;

/** The school's list for a month (M1-16's /materials/school/build), for the coordinator, and for the staff preview
 * worked out and not kept; null when the person may not see it, and the page says so. */
export async function schoolListOf(me: Pick<Session, "email">, from: string, to: string): Promise<SchoolList | null> {
  const res = await engineSend("/materials/school/build", { actor: me.email, from, to });
  if (res.status === 403) return null;
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}).`);
  return (await res.json()) as SchoolList;
}

/** The notes waiting for a person, oldest first (M1-16's /materials/review/list); null when not hers to read. */
export async function waitingNotes(me: Pick<Session, "email">): Promise<WaitingNote[] | null> {
  const res = await engineSend("/materials/review/list", { actor: me.email });
  if (res.status === 403) return null;
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}).`);
  return ((await res.json()) as { notes: WaitingNote[] }).notes;
}

/** An activity's page, part by part (M1-12b's /curriculum/page/read). */
export const pageOf = (me: Pick<Session, "email">, code: string) => read<ActivityPage, "/curriculum/page/read">("/curriculum/page/read", { actor: me.email, code });
