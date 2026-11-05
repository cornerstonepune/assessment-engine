import type { Period } from "./types";

// The one rule for a period's chip on every screen (M1-09): Do now while it runs, Coming up before, To confirm when a
// part waits for her, Done or Late only from what was recorded (a note, M1-04), and none for a fixed or empty period.
// Over and unrecorded is no chip: the screen never guesses that work was missed.
export type Chip = "doNow" | "toConfirm" | "comingUp" | "done" | "late";

export function chipOf(
  p: Pick<Period, "starts_at" | "ends_at" | "kind" | "state">,
  at: { now: string; day: "past" | "today" | "future"; toConfirm?: boolean },
): Chip | null {
  if (p.kind === "fixed" || p.kind === "empty") return null;
  if (p.state === "done") return "done";
  if (p.state === "not_done") return "late";
  if (at.day === "future") return at.toConfirm ? "toConfirm" : "comingUp";
  if (at.day === "past") return null;
  const running = p.starts_at <= at.now && (p.ends_at === null || at.now < p.ends_at);
  if (running) return "doNow";
  if (at.toConfirm) return "toConfirm";
  return at.now < p.starts_at ? "comingUp" : null;
}
