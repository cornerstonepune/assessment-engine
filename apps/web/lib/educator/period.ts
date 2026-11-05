import type { Period } from "./types";

// What a period is called and when it is, said once for every screen (M1-09).

/** A period with no end (the bus) lasts until the next one starts; the day's last one keeps none. */
export const withEnds = <P extends Pick<Period, "starts_at" | "ends_at">>(ps: P[]): P[] =>
  ps.map((p, i) => (p.ends_at === null && ps[i + 1] ? { ...p, ends_at: ps[i + 1].starts_at } : p));

/** Its time as time: "09:40–10:00", or "13:25" when it has no end. */
export const timeOf = (p: Pick<Period, "starts_at" | "ends_at">) => `${p.starts_at}${p.ends_at ? `–${p.ends_at}` : ""}`;

/** The frame's name for it ("Academic 2 General Awareness"): a break by its own words, a lesson by the frame's text up
 * to the planner's line. */
export function nameOf(p: Pick<Period, "kind" | "label" | "text" | "line">): string {
  if (p.kind === "fixed") return p.label;
  const cut = p.line ? p.text.lastIndexOf(": ") : -1;
  return cut > 0 ? p.text.slice(0, cut) : p.text || p.label;
}

/** A day in the address: YYYY-MM-DD and a real date, or nothing. */
export const isDay = (s: string | undefined): s is string => !!s && /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(`${s}T00:00:00Z`));
