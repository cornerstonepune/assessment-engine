// The engine's answers the K2 educator's screens read (agreed with M1-06, 4 Nov; /activity is engine/w2_print/k2_activity.py).
export type ClassRef = { id: string; grade: string; section: string };
export type PeriodKind = "fixed" | "subject" | "specialist" | "empty";
export type SessionState = "planned" | "done" | "not_done" | "moved";
export type Period = {
  period_id: string;
  starts_at: string;
  ends_at: string | null;
  label: string;
  /** What it is called (M1-06e): a break by its own words, a lesson by the frame's ("Academic 2 General Awareness"). */
  name: string;
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
/** One period (M1-06's /timetable/period): the period, its day, and the planner's lines under the same heading. */
export type OnePeriod = Period & { classes: ClassRef[]; class: ClassRef; frozen: boolean; day: string; note: string | null; week: "A" | "B" | null; fortnight: Fortnight | null; plan_lines: string[] };

/** Where an item is kept: the class's own, the school's store, or not tracked (M1-10). */
export type Home = "class" | "school" | null;
export type MaterialLine = {
  line_id: string;
  item: string;
  material_code: string;
  quantity: number | null;
  unit: string;
  needed_on: string;
  activity: { id: string; code: string; name: string } | null;
  source: "school" | "educator";
  home: Home;
  tracked: boolean;
};
/** A class's materials list (M1-10's /materials/read), each day its own group. */
export type MaterialsList = {
  list_id: string;
  from: string;
  to: string;
  state: "draft" | "sent";
  groups: { label: string; lines: MaterialLine[] }[];
};
export type CatalogueItem = { code: string; name: string; unit: string; home: Home; tracked: boolean };
/** The school's list for a range (M1-16's /materials/school/read): each item once, with the classes it comes from. */
export type SchoolList = {
  id: string;
  from: string;
  to: string;
  lines: { material_code: string; item: string; quantity: number | null; unit: string; to_confirm: boolean; from: { class_id: string; class: string; quantity: number | null; activity_codes: string[] }[] }[];
};
/** A note the system could not read for sure, waiting for a person (M1-16's /materials/review/list). */
export type WaitingNote = { id: string; list_id: string; text: string; reason: string; at: string };

/** An activity's page (M1-12b's /curriculum/page/read): its parts as the shared page-part component draws them. */
export type ActivityPage = {
  code: string;
  name: string;
  section: string;
  parts: import("../page-part").PagePart[];
  materials: { text: string; items: { name: string; quantity: number | null; unit: string }[] };
};
