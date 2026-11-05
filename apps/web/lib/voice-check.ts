import { MARKS, type MarkKey, W } from "./voice-words";

// What the Confirm page and the form hold while she works, and what stops Confirm (task M1-04): pure, so a test reads
// every rule without a database or a browser. The engine checks it all again when she confirms (voice_confirm.py); this
// is so she sees the problem before she presses, each with its fix. A child is a roll number (Sr. No.), never a name.

/** One line of the engine's draft (POST /voice/notes/draft). */
export type DraftLine = { section: string; words: string; numbers: number[]; text: string | null; said: boolean; problems: string[]; notes: string[] };
export type Draft = {
  note_id: string;
  status: string;
  received_at: string;
  kind: string;
  taught_on: string;
  activity: string | null;
  level: number;
  day_problems: string[];
  /** any words came back from the recording: none is "nothing heard", some with no line read is "could not read" */
  heard: boolean;
  lines: DraftLine[];
  problems: string[];
  enrolled: string[];
  blocked: boolean;
};
export type Activity = { code: string; no: string; name: string };

/** roll → the marks it carries; more than one is a problem until she keeps one. */
export type Marks = Record<string, MarkKey[]>;
export type Work = {
  activity: string | null;
  level: number | null;
  day: string;
  rest: boolean;
  marks: Marks;
  /** sections whose engine problems she has dealt with (painted with that mark, or said it is right as it is) */
  settled: string[];
  /** the day was picked by her, so the engine's problems about the date she said are gone */
  dayPicked: boolean;
};

export type Problem =
  | { key: string; kind: "stranger"; roll: string; text: string }
  | { key: string; kind: "two"; roll: string; marks: MarkKey[]; text: string }
  | { key: string; kind: "activity"; text: string }
  | { key: string; kind: "level"; text: string }
  | { key: string; kind: "day"; text: string }
  | { key: string; kind: "line"; section: string; text: string };

const isMark = (s: string): s is MarkKey => (MARKS as readonly string[]).includes(s);

/** The work as the draft says it: every number heard under its own mark, the rest as she said it, nothing she did not say. */
export function fromDraft(d: Draft): Work {
  const marks: Marks = {};
  for (const line of d.lines)
    if (isMark(line.section))
      for (const n of line.numbers) {
        const had = (marks[String(n)] ??= []);
        if (!had.includes(line.section)) had.push(line.section);
      }
  return {
    activity: d.activity,
    level: d.level,
    day: d.taught_on,
    rest: d.lines.some((l) => l.section === "rest" && l.said),
    marks,
    settled: [],
    dayPicked: false,
  };
}

/** The form starts empty: nothing ticked, the rest off, today. */
export const blankWork = (today: string): Work => ({ activity: null, level: null, day: today, rest: false, marks: {}, settled: [], dayPicked: true });

/** Paint one child with the chosen mark; the same mark again takes it off. */
export function paint(w: Work, roll: string, mark: MarkKey | "clear"): Work {
  const marks = { ...w.marks };
  if (mark === "clear" || (marks[roll]?.length === 1 && marks[roll][0] === mark)) delete marks[roll];
  else marks[roll] = [mark];
  const settled = mark === "clear" || w.settled.includes(mark) ? w.settled : [...w.settled, mark];
  return { ...w, marks, settled };
}

/** #31's mark moved onto the child she taps (a number heard that is not in the class). */
export function moveTo(w: Work, from: string, to: string): Work {
  const marks = { ...w.marks };
  const moved = marks[from] ?? [];
  delete marks[from];
  if (moved.length) marks[to] = [...moved];
  return { ...w, marks };
}

/** The red problems, in the order she meets them: the class's numbers first, then the activity, level, date and lines. */
export function problemsOf(w: Work, ctx: { enrolled: readonly string[]; klass: string; activities: readonly Activity[]; today: string; draft?: Draft }): Problem[] {
  const out: Problem[] = [];
  const word = (m: MarkKey) => W.marks[m];
  for (const [roll, ms] of Object.entries(w.marks).sort(([a], [b]) => a.localeCompare(b, "en", { numeric: true }))) {
    if (!ctx.enrolled.includes(roll)) out.push({ key: `stranger:${roll}`, kind: "stranger", roll, text: W.problems.stranger(roll, ctx.klass) });
    else if (ms.length > 1) out.push({ key: `two:${roll}`, kind: "two", roll, marks: ms, text: W.problems.twoLists(roll, word(ms[0]), word(ms[1])) });
  }
  if (!w.activity || !ctx.activities.some((a) => a.code === w.activity)) {
    const said = ctx.draft?.lines.find((l) => l.section === "activity")?.numbers[0];
    out.push({ key: "activity", kind: "activity", text: said === undefined ? W.activity.none : W.activity.notFound(said) });
  }
  if (w.level === null || !(W.level.values as readonly number[]).includes(w.level)) out.push({ key: "level", kind: "level", text: W.problems.level });
  if (w.day > ctx.today) out.push({ key: "day", kind: "day", text: W.day.future });
  else if (!w.dayPicked && ctx.draft?.day_problems.length) out.push({ key: "day", kind: "day", text: W.day.unread });
  for (const line of ctx.draft?.lines ?? []) {
    // a list's own trouble (a word not read, a correction with no number) is hers to settle; the number checks are above
    const own = line.problems.filter((p) => !p.startsWith("#"));
    if (own.length && isMark(line.section) && !w.settled.includes(line.section))
      out.push({ key: `line:${line.section}`, kind: "line", section: line.section, text: W.problems.unread(W.marks[line.section]) });
  }
  return out;
}

/** "1 above, 2 below, 1 absent, 18 as expected = 22", or, with the rest not said, "3 named; the other 19 not seen". */
export function countLine(w: Work, enrolled: readonly string[]): string {
  const named = Object.keys(w.marks).filter((r) => enrolled.includes(r));
  const rest = enrolled.length - named.length;
  if (!w.rest) return W.count.named(named.length, rest);
  const parts = MARKS.map((m) => [m, named.filter((r) => w.marks[r][0] === m).length] as const)
    .filter(([, n]) => n)
    .map(([m, n]) => `${n} ${W.marks[m].toLowerCase()}`);
  return [...parts, `${rest} ${W.marks.as_expected.toLowerCase()}`].join(", ") + ` = ${enrolled.length}`;
}

/** What is sent to the engine: each roll under its one mark. */
export function listsOf(w: Work): Record<MarkKey, string[]> {
  const out = { above: [], below: [], not_willing: [], absent: [] } as Record<MarkKey, string[]>;
  for (const [roll, ms] of Object.entries(w.marks)) if (ms.length === 1) out[ms[0]].push(roll);
  return out;
}

/** An activity found by its number on the K2 list, or by a word of its name. */
export function findActivities(all: readonly Activity[], q: string, most = 8): Activity[] {
  const t = q.trim().toLowerCase();
  if (!t) return [];
  const byNo = all.filter((a) => a.no && a.no === t);
  const byName = all.filter((a) => !byNo.includes(a) && ((a.no && a.no.startsWith(t)) || a.name.toLowerCase().includes(t)));
  return [...byNo, ...byName].slice(0, most);
}

/** An activity as she reads it: "12 · Sorting by colour", or its name alone when the sheet gave it no number. */
export const activityWords = (a: Activity) => (a.no ? `${a.no} · ${a.name}` : a.name);

/** Days between the day it was taught and the day it reached us, on the school's clock: 0 is today's note, 1 is
 *  "late: about yesterday". */
export function daysLate(taughtOn: string, receivedAt: string, zone: string): number {
  const heard = new Date(receivedAt).toLocaleDateString("en-CA", { timeZone: zone });
  return Math.round((Date.parse(heard) - Date.parse(taughtOn)) / 86_400_000);
}
