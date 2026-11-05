import type { Period } from "./types";

// The one rule for a period's chip on every screen (M1-09, D-075): Do now while it runs, To confirm when a part waits
// for her, Done or Late only from what was recorded (a note, M1-04); none on a period still to come (the countdown says
// when), none on a fixed or empty period, and none over and unrecorded: the screen never guesses that work was missed.
export type Chip = "doNow" | "toConfirm" | "comingUp" | "done" | "late";

export function chipOf(
  p: Pick<Period, "starts_at" | "ends_at" | "kind" | "state">,
  at: { now: string; day: "past" | "today" | "future"; toConfirm?: boolean },
): Chip | null {
  if (p.kind === "fixed" || p.kind === "empty") return null;
  if (p.state === "done") return "done";
  if (p.state === "not_done") return "late";
  if (at.day === "future") return at.toConfirm ? "toConfirm" : null;
  if (at.day === "past") return null;
  const running = p.starts_at <= at.now && (p.ends_at === null || at.now < p.ends_at);
  if (running) return "doNow";
  if (at.toConfirm) return "toConfirm";
  return null;
}

/** Where today's Now line falls: the index of the first period still to come (after the one running), or null before
 * the day starts and after it ends. */
export function nowAt(ps: Pick<Period, "starts_at" | "ends_at">[], now: string): number | null {
  if (!ps.length || now < ps[0].starts_at) return null;
  const last = ps[ps.length - 1];
  if (now >= (last.ends_at ?? last.starts_at)) return null;
  const i = ps.findIndex((p) => p.starts_at > now);
  return i === -1 ? ps.length : i;
}

/** "in 25 min", "in 1 h 5 min": time shown as time (D-075). */
export function countdown(from: string, to: string): string {
  const m = (s: string) => Number(s.slice(0, 2)) * 60 + Number(s.slice(3, 5));
  const d = m(to) - m(from);
  return d >= 60 ? `in ${Math.floor(d / 60)} h${d % 60 ? ` ${d % 60} min` : ""}` : `in ${d} min`;
}
