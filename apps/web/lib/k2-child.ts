// What a K2 child's page and the class picture say, in the school's words (task M1-17). Pure: no database, no engine.
// The engine answers in codes and numbers (`POST /k2/child`, `POST /k2/picture`); this file turns them into words, a tone
// and an icon. Colour is never the only sign (D-075): every state is an icon and a word. A child's state is never red:
// terracotta is for late or missing work, and `act` is not a tone a child can have (the test below the table holds it).
import type { IconName } from "./icons";

export type ChildTone = "ok" | "wait" | "quiet";

// The words are the school's (K2 team). `emerging` is the engine's "under half right", a written-paper phrase that means
// nothing for an observed skill, so it is "just starting" here. Unverified with the school.
export const CHILD_STATES: Record<string, { words: string; tone: ChildTone; icon: IconName }> = {
  secure: { words: "secure", tone: "ok", icon: "secure" },
  stretch_ready: { words: "ready to move up", tone: "ok", icon: "secure" },
  secure_to_recheck: { words: "secure, to re-check", tone: "wait", icon: "re-check" },
  practising: { words: "practising", tone: "wait", icon: "practising" },
  patterned_error: { words: "repeating a mistake", tone: "wait", icon: "practising" },
  emerging: { words: "just starting", tone: "quiet", icon: "emerging" },
  not_enough_yet: { words: "not enough yet", tone: "quiet", icon: "not-enough" },
};
const UNKNOWN = { words: "seen", tone: "quiet", icon: "not-enough" } as const;
export const childState = (code: string) => CHILD_STATES[code] ?? UNKNOWN;

export type Trend = "up" | "steady" | "down" | "too_few";
// A trend, never a score. "Down" is said gently and is not red: a child can have a month with less.
export const TRENDS: Record<Trend, { words: string; icon: IconName }> = {
  up: { words: "moving up", icon: "above" },
  steady: { words: "steady", icon: "as-expected" },
  down: { words: "lower this month", icon: "below" },
  too_few: { words: "too few months to say", icon: "not-enough" },
};

export type SkillRef = { code: string; name: string };
export type PlanSkill = SkillRef & { state: string; words: string; level: number | null; last_seen: string; sentence: string | null; sentence_note: string | null };
export type Growth = { skill: SkillRef; first_seen: string; last_seen: string; by_month: { month: string; level: number; days: number }[]; trend: Trend };
export type ReadyNext = { skill: SkillRef; because: { before: SkillRef; strength: string }[] };
export type ChildPage = { class: string; roll_no: string; skills: PlanSkill[]; growth: Growth[]; ready_next: ReadyNext[] };
export type Cell = { state: string; words: string; level: number | null; last_seen: string };
export type ClassPicture = { class: string; skills: SkillRef[]; children: { roll_no: string; cells: Record<string, Cell> }[] };

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2026-10" → "Oct 2026". */
export const monthWords = (m: string) => `${MONTHS[Number(m.slice(5, 7)) - 1] ?? m.slice(5, 7)} ${m.slice(0, 4)}`;
/** "2026-10-19" → "19 Oct". */
export const dayWords = (d: string) => `${Number(d.slice(8, 10))} ${MONTHS[Number(d.slice(5, 7)) - 1] ?? ""}`;
/** A level the educator gave, 0 to 3. A named observation with no level (a group line) says nothing. */
export const levelWords = (l: number | null) => (l === null ? "no level named" : `level ${l} of 3`);

/** A class's skills in the order the picture shows them, with how many children were seen on each. */
export function seenCounts(p: ClassPicture): Record<string, number> {
  const n: Record<string, number> = {};
  for (const c of p.children) for (const code of Object.keys(c.cells)) n[code] = (n[code] ?? 0) + 1;
  return n;
}
