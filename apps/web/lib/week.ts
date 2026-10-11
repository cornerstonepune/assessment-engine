// The week a paper is made for, as the engine names it: a child's next paper is one per ISO week.
/** The ISO week, "2026-W39": a paper chosen in one week is the same paper however often the page opens. */
export function isoWeek(d = new Date()): string {
  const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  const first = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const n = Math.ceil(((t.getTime() - first.getTime()) / 86_400_000 + 1) / 7);
  return `${t.getUTCFullYear()}-W${String(n).padStart(2, "0")}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** An ISO week said as a person says it, by its Monday: "2026-W41" is "week of 5 Oct". A week named any other way (a
 *  test's own, an old paper's) is shown as it is: it names no dates to say. */
export function weekWords(week: string): string {
  const m = /^(\d{4})-W(\d{2})$/.exec(week);
  if (!m) return week;
  // week 1 is the one holding 4 January; its Monday is the Monday on or before it
  const jan4 = new Date(Date.UTC(Number(m[1]), 0, 4));
  const monday = new Date(jan4.getTime() + (1 - (jan4.getUTCDay() || 7) + (Number(m[2]) - 1) * 7) * 86_400_000);
  return `week of ${monday.getUTCDate()} ${MONTHS[monday.getUTCMonth()]}`;
}
