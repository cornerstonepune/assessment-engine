import { EngineDown, engineSend } from "./engine";

// The timetable's rules as the site reads them (task M1-14 part a). Every check, every write and the history are the
// engine's (routes/timetable_rules.py); the site shows what it answers and says why when it refuses. No name is kept here.

export type Period = { id: string; ord: number; label: string; starts_at: string; ends_at: string | null; fixed: boolean };
export type Fixed = { id: string; period_id: string; label: string; weekday: number; week: "A" | "B"; text: string };
export type Block = { id: string; on_date: string | null; weekday: number | null; week: "A" | "B" | null; period_id: string | null; period: string | null; reason: string };
export type Limit = { id: string; subject_code: string; span: "week" | "fortnight"; fewest: number | null; most: number | null };
export type Edit = { id: string; rule: "period" | "block" | "limit" | "fixed"; action: "set" | "remove"; who: string; at: string; before: Record<string, unknown> | null; after: Record<string, unknown> | null };
export type Rules = {
  classes: { id: string; grade: string; section: string }[];
  class: { id: string; grade: string; section: string };
  periods: Period[];
  fixed: Fixed[];
  blocks: Block[];
  limits: Limit[];
  subjects: { code: string; name: string }[];
  placed: Record<string, { A: number; B: number }>;
  history: Edit[];
};

/** The class's rules, or null when no class has a timetable yet (the page says so). */
export async function rulesOf(email: string, classId?: string): Promise<Rules | null> {
  const res = await engineSend("/timetable/rules/read", { actor: email, class_id: classId ?? null });
  if (res.status === 404) return null;
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}).`);
  return (await res.json()) as Rules;
}

/** The engine's own words for a refusal, or ours when it said none. */
export async function refusal(res: Response, fallback: string): Promise<string> {
  const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
  return typeof body.detail === "string" ? body.detail : fallback;
}

export const DAYS = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"] as const;
export const day = (n: number) => DAYS[n] ?? "";

/** A block in words: "Wed 25 Nov", or "Every Wednesday (week A)". */
export function blockWhen(b: Block): string {
  if (b.on_date) {
    const d = new Date(`${b.on_date}T00:00:00Z`);
    return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  }
  return `Every ${day(b.weekday ?? 0)}${b.week ? ` (week ${b.week})` : ""}`;
}

/** How many periods of a subject sit in the span now, against its limit: "over" and "under" are what needs a look. */
export function standing(l: Limit, placed: Rules["placed"]): { now: number; state: "within" | "over" | "under" } {
  const p = placed[l.subject_code] ?? { A: 0, B: 0 };
  const now = l.span === "week" ? Math.max(p.A, p.B) : p.A + p.B;
  const least = l.span === "week" ? Math.min(p.A, p.B) : now;
  if (l.most !== null && now > l.most) return { now, state: "over" };
  if (l.fewest !== null && least < l.fewest) return { now: least, state: "under" };
  return { now, state: "within" };
}
