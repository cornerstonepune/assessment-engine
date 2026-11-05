// The engine's answers the K2 educator's screens read (agreed with M1-06, 4 Nov; /activity is engine/w2_print/k2_activity.py).
export type ClassRef = { id: string; grade: string; section: string };
export type PeriodKind = "fixed" | "subject" | "specialist" | "empty";
export type SessionState = "planned" | "done" | "not_done" | "moved";
export type Period = {
  period_id: string;
  starts_at: string;
  ends_at: string | null;
  label: string;
  fixed: boolean;
  kind: PeriodKind;
  subject: string | null;
  text: string;
  line: string | null;
  state: SessionState;
  activity: { id: string; code: string; name: string } | null;
  plan_entry_id?: string | null;
};
export type Fortnight = { number: number; starts_on: string; ends_on: string };
export type DayKind = "teaching" | "holiday" | "changed_timing" | "none";
export type Day = {
  classes: ClassRef[];
  class: ClassRef;
  day: string;
  kind: DayKind;
  note: string | null;
  week: "A" | "B" | null;
  fortnight: Fortnight | null;
  frozen: boolean;
  periods: Period[];
};
export type Week = {
  classes: ClassRef[];
  class: ClassRef;
  week_of: string;
  week: "A" | "B" | null;
  fortnight: Fortnight | null;
  frozen: boolean;
  days: { day: string; weekday: number; kind: DayKind; note: string | null; periods: Period[] }[];
};
import type { BodyOf } from "../engine";

/** A part of an activity she may correct: the engine's own list (engine/api/routes/activity.py). */
export type EditablePart = BodyOf<"/activity/edit">["field"];
/** One period (M1-06's /timetable/period): the period, its day, and the planner's lines under the same heading. */
export type OnePeriod = Period & { classes: ClassRef[]; class: ClassRef; frozen: boolean; day: string; note: string | null; week: "A" | "B" | null; fortnight: Fortnight | null; plan_lines: string[] };
