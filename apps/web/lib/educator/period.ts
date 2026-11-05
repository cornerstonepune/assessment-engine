import type { Day, Period } from "./types";
import { E } from "./words";

// When a period is, and what kind of day it is, said once for every screen (M1-09). The engine says when each period
// ends and what it is called (M1-06e).

/** Its time as time: "09:40–10:00", or "13:25" when it has no end. */
export const timeOf = (p: Pick<Period, "starts_at" | "ends_at">) => `${p.starts_at}${p.ends_at ? `–${p.ends_at}` : ""}`;

/** A lesson: a period with work in it, not a break and not an empty slot. */
export const isLesson = (p: Pick<Period, "kind">) => p.kind !== "fixed" && p.kind !== "empty";

/** A day with nothing to draw, and what it says instead. */
export const isBlank = (d: Pick<Day, "kind" | "periods">) => d.kind === "holiday" || d.kind === "none" || d.periods.length === 0;
export const blankWords = (d: Pick<Day, "kind" | "note">) => (d.kind === "holiday" ? `${E.dayKind.holiday}${d.note ? `: ${d.note}` : ""}` : E.dayKind.none);

/** A day in the address: YYYY-MM-DD and a real date, or nothing. */
export const isDay = (s: string | undefined): s is string => !!s && /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(`${s}T00:00:00Z`));
