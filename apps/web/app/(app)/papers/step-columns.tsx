import { StatusChip } from "@/components/status-chip";
import { STEP_WORDS, STEPS, type Cell, type Counts, type Step } from "@/lib/assessment-steps";
import type { AssessmentRow, PaperListRow, Stage } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";

/** An assessment's copies as the counts the steps are read from: a copy replaced by a newer one is none of its copies. */
export const countsOf = (a: Pick<AssessmentRow, "by" | "unread" | "kind">): Counts => ({ by: a.by, unread: a.unread, home: a.kind === "focus" });

/** A child's paper as the same counts, of one. */
export const countsOfPaper = (p: Pick<PaperListRow, "stage" | "answers" | "kind">): Counts => {
  const by = { made: 0, printed: 0, scanned: 0, checked: 0, "signed off": 0 };
  const stage: Exclude<Stage, "replaced"> | null = p.stage === "replaced" ? null : p.stage;
  if (stage) by[stage] += 1;
  return { by, unread: p.stage === "scanned" && p.answers === 0 ? 1 : 0, home: p.kind === "focus" };
};

/** One step as a chip: done, how far on, the next to do, or not yet. */
function stepChip(c: Cell | undefined) {
  if (!c) return null;
  return <StatusChip state={c.state} words={c.note} compact />;
}

/** The columns of the steps, in the order the school does them. A step the row does not have (a class assessment's
 *  approval) is an empty cell, and a column empty on every row is not drawn. */
const WIDTHS: Record<Step, string> = { approve: "7.2%", made: "6.4%", printed: "7.2%", uploaded: "7.6%", read: "6.4%", checked: "7.2%", signedOff: "6.8%" };

export function stepColumns<T>(cells: (row: T) => Cell[]): Column<T>[] {
  return STEPS.map((step: Step) => ({
    key: step,
    label: STEP_WORDS[step],
    width: WIDTHS[step],
    status: true,
    value: (r: T) => cells(r).find((c) => c.step === step)?.state ?? null,
    cell: (r: T) => stepChip(cells(r).find((c) => c.step === step)),
  }));
}

