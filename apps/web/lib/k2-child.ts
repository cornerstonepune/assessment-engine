// What a K2 child's page and the class picture say (task M1-17). Pure: no database, no engine. The engine answers with the
// school's words and colours (`POST /k2/child`, `POST /k2/picture`); this file turns a colour into a tone and an icon, and a
// trend and a date into words. Colour is never the only sign (D-075): every state is an icon and a word.
import type { IconName } from "./icons";
import { dateWords } from "./week";

export type ChildTone = "ok" | "wait" | "quiet";

// A state's words and colour are the school's `child_state` rows: the engine sends them with every cell, and no code names a
// state (tests/test_states_and_subject.py). All this file adds is how a colour looks on a child: a tone and an icon, never
// colour alone. A child is never red (D-075): the rows' red reads as quiet, because terracotta is for late or missing work.
// Open point for the school: the row for the lowest state says "under half right", a written-paper phrase.
export const CHILD_LOOK: Record<string, { tone: ChildTone; icon: IconName }> = {
  green: { tone: "ok", icon: "done" },
  amber: { tone: "wait", icon: "to-confirm" },
  red: { tone: "quiet", icon: "to-do" },
  grey: { tone: "quiet", icon: "not-enough" },
};
export const lookOf = (colour: string) => CHILD_LOOK[colour] ?? CHILD_LOOK.grey;

export type Trend = "up" | "steady" | "down" | "too_few";
// A trend, never a score. "Down" is said gently and is not red: a child can have a month with less.
export const TRENDS: Record<Trend, { words: string; icon: IconName }> = {
  up: { words: "moving up", icon: "above" },
  steady: { words: "steady", icon: "as-expected" },
  down: { words: "lower this month", icon: "below" },
  too_few: { words: "too few months to say", icon: "not-enough" },
};

export type SkillRef = { code: string; name: string };
export type PlanSkill = SkillRef & { state: string; words: string; colour: string; level: number | null; last_seen: string; sentence: string | null; sentence_note: string | null };
export type Growth = { skill: SkillRef; first_seen: string; last_seen: string; by_month: { month: string; level: number; days: number }[]; trend: Trend };
export type ReadyNext = { skill: SkillRef; because: { before: SkillRef; strength: string }[] };
export type ChildPage = { class: string; roll_no: string; skills: PlanSkill[]; growth: Growth[]; ready_next: ReadyNext[] };
export type Cell = { state: string; words: string; colour: string; level: number | null; last_seen: string };
export type ClassPicture = { class: string; skills: SkillRef[]; children: { roll_no: string; cells: Record<string, Cell> }[] };

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2026-10" → "Oct 2026". */
export const monthWords = (m: string) => `${MONTHS[Number(m.slice(5, 7)) - 1] ?? m.slice(5, 7)} ${m.slice(0, 4)}`;
/** A day as every page of the site says it: "19-Oct-2026". */
export const dayWords = dateWords;
/** A level the educator gave, 0 to 3. A named observation with no level (a group line) says nothing. */
export const levelWords = (l: number | null) => (l === null ? "no level named" : `level ${l} of 3`);

/** How many children were seen on each skill of the class picture, by skill code. */
export function seenCounts(p: ClassPicture): Record<string, number> {
  const n: Record<string, number> = {};
  for (const c of p.children) for (const code of Object.keys(c.cells)) n[code] = (n[code] ?? 0) + 1;
  return n;
}
