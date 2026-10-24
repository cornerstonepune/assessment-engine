// An assessment on the Assessments page (goals/asm_assessments_page.yaml): its name, built from the sheet's own code, and
// the steps it has been through, in the order the school does them. Pure: no rows are read here, so a test can hold it.
// Nimish, 2026-10-24: "we should not use these file names, because if we know the assessment code, there is a QR inside
// these files. That QR is associated with a certain topic, so we can actually show proper names."

import type { State } from "@/components/status-chip";
import { dateWords } from "./week";

/** What the sheet's code says, in the school's words: the skill and level (or a whole paper's title), its kind, its class,
 *  the day it was made, said as every page says a date — "Equal groups (repeated addition) · Easy · Grade 1 · class assessment · 19-Oct-2026". A part the
 *  sheet does not carry is left out, never written as a dash. */
export function builtName(p: { title: string; kind: string; kinds: Record<string, string>; classWords: string | null; day: string | null }): string {
  const kind = (p.kinds[p.kind] ?? p.kind).toLowerCase();
  // "Home assessments" already says its kind
  return [p.title, p.classWords, p.title.toLowerCase().includes(kind) ? null : kind, p.day ? dateWords(p.day.slice(0, 10)) : null].filter(Boolean).join(" · ");
}

/** The name an educator chose, else the built one. `chosen` is the newest row for the assessment's key. */
export const nameOf = (chosen: string | null | undefined, built: string) => (chosen?.trim() ? chosen.trim() : built);

// --- the steps ---

export const STEPS = ["approve", "made", "printed", "uploaded", "read", "checked", "signedOff"] as const;
export type Step = (typeof STEPS)[number];

export const STEP_WORDS: Record<Step, string> = {
  approve: "To approve",
  made: "Made",
  printed: "Printed / given",
  uploaded: "Uploaded",
  read: "Read",
  checked: "Checked",
  signedOff: "Signed off",
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
export function matchFiles(scans: ScanFile[], owner: Map<string, string>, known: Set<string>): { byKey: Map<string, string[]>; unmatched: string[] } {
  const byKey = new Map<string, string[]>();
  const unmatched: string[] = [];
  for (const s of scans) {
    const keys = new Set(s.codes.flatMap((c) => (owner.has(c) ? [owner.get(c)!] : [])));
    for (const k of keys) byKey.set(k, [...new Set([...(byKey.get(k) ?? []), s.file])]);
    if (!s.codes.some((c) => known.has(c))) unmatched.push(s.file);
  }
  return { byKey, unmatched: [...new Set(unmatched)] };
}
