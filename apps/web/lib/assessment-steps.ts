// An assessment on the Assessments page (goals/asm_assessments_page.yaml): its name, built from the sheet's own code, and
// the steps it has been through, in the order the school does them. Pure: no rows are read here, so a test can hold it.
// Nimish, 2026-10-24: "we should not use these file names, because if we know the assessment code, there is a QR inside
// these files. That QR is associated with a certain topic, so we can actually show proper names."

import type { State } from "@/components/status-chip";
import { dateWords } from "./week";

/** What an assessment is made of, as the rows say it: the topics and skills its questions are on, the levels of its copies,
 *  its kind, its class, and the day it was made. Every word is a row (topic, skill, difficulty, grade, class); only the way
 *  they are joined is here. */
export type NameFacts = {
  /** A whole paper's own title: the name where no skill names it. */
  title: string;
  topics: string[];
  skills: string[];
  levels: string[];
  kind: string;
  kinds: Record<string, string>;
  classWords: string | null;
  /** The roll number, where the assessment is one child's alone. */
  roll?: string | null;
  day: string | null;
};

/** An assessment as a teacher would say it (Nimish, 26 Oct 2026: "the composition of the assessment is what you're showing
 *  here, which is not at all useful... the nomenclature can be better"): topic · skill · level · kind · class · day, for
 *  example "Addition & subtraction · 2-digit + 2-digit · Easy · Home assessment · Grade 1 · 12-Oct-2026". Three or more
 *  skills are counted, never listed, and levels that differ are left out: the list of them is in the detail view. A part the
 *  sheet does not carry is left out, never written as a dash. */
export function builtName(p: NameFacts): string {
  const kind = p.kinds[p.kind] ?? p.kind;
  const topic = p.topics.length > 2 ? "Mixed topics" : p.topics.join(" + ");
  const what = p.skills.length === 0 ? p.title : p.skills.length > 2 ? `${p.skills.length} skills` : p.skills.join(", ");
  const parts = [
    topic && topic !== what ? topic : null,
    what,
    p.levels.length === 1 && !what.endsWith(p.levels[0]) ? p.levels[0] : null,
    // a title that already says its kind ("Home assessments") is not given it twice
    what.toLowerCase().includes(kind.toLowerCase()) ? null : kind,
    p.classWords ? `${p.classWords}${p.roll ? ` roll ${p.roll}` : ""}` : null,
    p.day ? dateWords(p.day.slice(0, 10)) : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

/** The name an educator chose, else the built one. `chosen` is the newest row for the assessment's key. */
export const nameOf = (chosen: string | null | undefined, built: string) => (chosen?.trim() ? chosen.trim() : built);

// --- the steps ---

export const STEPS = ["made", "approve", "printed", "uploaded", "read", "checked", "signedOff"] as const;
export type Step = (typeof STEPS)[number];

// The school's seven steps, in the order it does them (Nimish, 26 Oct 2026: "created, approved, printed, uploaded, read,
// checked, results in"): the pack built, the educator's approval, the paper printed and given, the scans in, the engine's
// reading, a person's check, and the results confirmed. A class assessment has no approval step of its own.
export const STEP_WORDS: Record<Step, string> = {
  made: "Created",
  approve: "Approved",
  printed: "Printed",
  uploaded: "Uploaded",
  read: "Read",
  checked: "Checked",
  signedOff: "Results in",
};

/** An assessment's live copies by the stage each stands at (`AssessmentRow.by`), and of those read-in, how many had no
 *  answer found yet. A copy replaced by a newer one is no copy of the assessment. */
export type Counts = {
  by: { made: number; printed: number; scanned: number; checked: number; "signed off": number };
  unread: number;
  /** A home assessment, made by the system for each child: it waits for an educator's approval. */
  home: boolean;
};

export type Cell = { step: Step; reached: number; total: number; state: State; note?: string };

/** How many copies have been through each step. Approval and print coincide for a home assessment: approving marks the
 *  pack printed, so both read the same until that changes. */
export function reachedBy(c: Counts): Record<Step, number> {
  const { made, printed, scanned, checked } = c.by;
  const signed = c.by["signed off"];
  const total = made + printed + scanned + checked + signed;
  const uploaded = scanned + checked + signed;
  return {
    approve: total - made,
    made: total,
    printed: total - made,
    uploaded,
    read: Math.max(0, uploaded - c.unread),
    checked: checked + signed,
    signedOff: signed,
  };
}

/** What an assessment asks of the educator next. What waits on a person now comes before what waits on paper to come back:
 *  an approval first (nothing prints without it), then answers to check, then papers to sign off, then to print, then
 *  to put the papers in, then the engine's own reading, and at last the results. */
export type Action = { kind: "approve" | "print" | "upload" | "reading" | "check" | "signoff" | "results" | "none"; label: string };

const STEP_OF: Record<Action["kind"], Step | null> = {
  approve: "approve",
  print: "printed",
  upload: "uploaded",
  reading: "read",
  check: "checked",
  signoff: "signedOff",
  results: null,
  none: null,
};

export function actionOf(c: Counts, waiting = 0): Action {
  const { made, scanned, checked } = c.by;
  const total = made + c.by.printed + scanned + checked + c.by["signed off"];
  if (total === 0) return { kind: "none", label: "Replaced by a newer one" };
  if (c.home && made > 0) return { kind: "approve", label: "Approve" };
  if (waiting > 0) return { kind: "check", label: `Check ${waiting} answer${waiting === 1 ? "" : "s"}` };
  if (checked > 0) return { kind: "signoff", label: `Sign off ${checked} paper${checked === 1 ? "" : "s"}` };
  if (made > 0) return { kind: "print", label: "Print" };
  if (c.by.printed > 0) return { kind: "upload", label: "Upload" };
  if (c.unread > 0) return { kind: "reading", label: "See reading" };
  if (scanned > 0) return { kind: "check", label: "Check" };
  return { kind: "results", label: "See results" };
}

// --- the stage, said as a row's signature ---

/** The eight facts `actionOf` reads, each as one digit: any copy made, printed, in, checked, signed off; any copy with no
 *  answer found yet; any answer waiting for a person; a home assessment. `actionOf` looks only at whether each is more than
 *  nothing, so a row's next step is known from this alone, and the database can group by it (`sigSql`) without a second copy
 *  of the rule. */
export const sigOf = (c: Counts, waiting: number) =>
  [c.by.made, c.by.printed, c.by.scanned, c.by.checked, c.by["signed off"], c.unread, waiting, c.home ? 1 : 0]
    .map((n) => (n > 0 ? 1 : 0))
    .join("");

/** Every signature whose next step is `kind`, for the database to filter by. */
export function sigsFor(kind: Action["kind"]): string[] {
  const out: string[] = [];
  for (let n = 0; n < 256; n++) {
    const bit = (i: number) => (n >> (7 - i)) & 1;
    const counts: Counts = {
      by: { made: bit(0), printed: bit(1), scanned: bit(2), checked: bit(3), "signed off": bit(4) },
      unread: bit(5),
      home: bit(7) === 1,
    };
    if (actionOf(counts, bit(6)).kind === kind) out.push(sigOf(counts, bit(6)));
  }
  return out;
}

/** The next step of a signature (`sigOf`). */
export function actionOfSig(sig: string): Action["kind"] {
  const b = [...sig].map(Number);
  return actionOf(
    { by: { made: b[0], printed: b[1], scanned: b[2], checked: b[3], "signed off": b[4] }, unread: b[5], home: b[7] === 1 },
    b[6],
  ).kind;
}

/** The steps of one assessment as cells: done (green), under way (amber, "9 of 28"), the one the next action is at (red
 *  where answers wait for the educator, amber otherwise), or not yet (grey). A class assessment has no approval step. */
export function stepCells(c: Counts, waiting = 0): { cells: Cell[]; next: Step | null; total: number } {
  const r = reachedBy(c);
  const total = r.made;
  const steps = STEPS.filter((s) => s !== "approve" || c.home);
  const next = STEP_OF[actionOf(c, waiting).kind];
  const cells = steps.map((step): Cell => {
    const reached = r[step];
    if (total > 0 && reached === total) return { step, reached, total, state: "done" };
    const part = reached > 0 ? { note: `${reached} of ${total}` } : {};
    if (step === next) {
      // red only where answers wait for the educator; the engine's own step (reading) and the rest are amber
      const state: State = step === "checked" ? "toCheck" : step === "read" ? "waiting" : "next";
      return { step, reached, total, state, ...part };
    }
    return reached > 0 ? { step, reached, total, state: "waiting", ...part } : { step, reached, total, state: "notYet" };
  });
  return { cells, next, total };
}

/** The furthest step reached and what comes after, said for a person ("Read · next: Checked"). */
export function standingWords(c: Counts, waiting = 0): string {
  const { cells, next } = stepCells(c, waiting);
  const done = [...cells].reverse().find((x) => x.state === "done");
  const after = next ? STEP_WORDS[next] : null;
  return `${done ? STEP_WORDS[done.step] : "Not started"}${after ? ` · next: ${after}` : " · all done"}`;
}

// --- files ---

type ScanFile = { file: string; codes: string[] };

/** Each file read, listed against the assessment its printed codes belong to; a file whose codes belong to none is
 *  "not matched". `known` is every code the school printed; `owner` maps a printed code to its assessment's key. */
export function matchFiles(
  scans: ScanFile[],
  owner: Map<string, string>,
  known: Set<string>,
): { byKey: Map<string, string[]>; unmatched: string[] } {
  const byKey = new Map<string, string[]>();
  const unmatched: string[] = [];
  for (const s of scans) {
    const keys = new Set(s.codes.flatMap((c) => (owner.has(c) ? [owner.get(c)!] : [])));
    for (const k of keys) byKey.set(k, [...new Set([...(byKey.get(k) ?? []), s.file])]);
    if (!s.codes.some((c) => known.has(c))) unmatched.push(s.file);
  }
  return { byKey, unmatched: [...new Set(unmatched)] };
}
