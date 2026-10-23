import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { KIND_WORDS, type AssessmentRow, type PaperListRow, type Stage } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";
import { dateWords, weekWords } from "@/lib/week";
import { CopiesTable, STAGE_STATE } from "./copies-table";

// A class's home assessments or chosen papers for a week are one assessment, named for what they are.
const MANY: Record<string, string> = { focus: "Home assessments", custom: "Chosen papers" };

/** Which assessment a paper or a row is: its kind, class, week and skill set or worksheet. */
export const assessmentKey = (a: { kind: string; section: string | null; week: string | null; set: string | null }) =>
  [a.kind, a.section ?? "", a.week ?? "", a.set ?? ""].join("~");

/** Its card (goals/s2-the-assessment-card.yaml): the assessment from Made to Results, with its next step. */
export const cardHref = (a: { kind: string; section: string | null; week: string | null; set: string | null }) => {
  const q = new URLSearchParams({ class: a.section ?? "", week: a.week ?? "", kind: a.kind, ...(a.set ? { set: a.set } : {}) });
  return `/papers/card?${q}`;
};

export const assessmentTitle = (a: AssessmentRow) => (a.set ? a.title : (MANY[a.kind] ?? a.title));

// Where an assessment stands, in two words each: the stage its furthest-behind copies are at, and what that asks of the
// educator. Answers waiting for a person come first (red), then the earliest stage with copies in it.
const STAGE_NAME: Record<Stage, string> = { made: "Made", printed: "Printed", scanned: "Papers in", checked: "Checked", "signed off": "Signed off", replaced: "Replaced" };
const ORDER: Stage[] = ["scanned", "made", "printed", "checked", "signed off", "replaced"];

export function standing(a: Pick<AssessmentRow, "by" | "waiting">): { stage: Stage; state: State; note?: string } {
  const stage = ORDER.find((s) => a.by[s]) ?? "signed off";
  return { stage, state: STAGE_STATE[stage], note: stage === "scanned" && a.waiting ? `${a.waiting} answer${a.waiting === 1 ? "" : "s"}` : undefined };
}

/** The copies of the assessment that are in: read, checked or signed off. */
const papersIn = (a: AssessmentRow) => Math.min(a.copies, a.by.scanned + a.by.checked + a.by["signed off"]);

type View = AssessmentRow & { subjectName: string | null; given: string | null };

// A week's assessments (goals/s2-the-assessment-card.yaml, goals/uxn1-design-system.yaml): one table, one row each —
// class, subject, the assessment (its name opening it in place to its copies, and closing it again), its kind, the stage
// it stands at, the day it was given, the copies that are in, and the one status chip. Newest first.
export async function AssessmentsTable({
  rows,
  copies,
  page,
  subjects,
  given,
  href,
  pageHref,
}: {
  rows: AssessmentRow[];
  copies: Map<string, PaperListRow[]>;
  page: number;
  subjects: Map<string, string>;
  given: Map<string, string>;
  href: (a: AssessmentRow, open: boolean) => string;
  pageHref: (page: number) => string;
}) {
  const g = await grades();
  const views: View[] = rows.map((a) => ({
    ...a,
    subjectName: a.subject ? (subjects.get(a.subject) ?? a.subject) : null,
    given: (a.qrs ?? []).map((q) => given.get(q)).filter(Boolean).sort().at(-1) ?? null,
  }));
  const columns: Column<View>[] = [
    { key: "class", label: "Class", width: "11%", keep: true, value: (a) => (a.section ? (a.band ? classWords(g, a.band, a.section) : a.section) : null) },
    { key: "subject", label: "Subject", width: "8%", value: (a) => a.subjectName },
    {
      key: "assessment",
      label: "Assessment",
      width: "24%",
      keep: true,
      value: (a) => assessmentTitle(a),
      cell: (a) => {
        const open = copies.has(assessmentKey(a));
        return (
          <>
            {/* the marker is drawn, not written: the line's words are the assessment's alone */}
            <Link
              href={href(a, open)}
              aria-expanded={open}
              className={`font-medium text-basalt before:mr-1 before:inline-block before:w-3 before:text-basalt/50 ${open ? "before:content-['▾']" : "before:content-['▸']"}`}
            >
              {assessmentTitle(a)}
            </Link>
            {a.week ? <span className="block pl-4 text-[12px] text-basalt/60">{weekWords(a.week)}</span> : null}
          </>
        );
      },
    },
    { key: "kind", label: "Kind", width: "11%", value: (a) => KIND_WORDS[a.kind] ?? a.kind },
    { key: "stage", label: "Stage", width: "9%", keep: true, value: (a) => STAGE_NAME[standing(a).stage] },
    { key: "given", label: "Given on", width: "10%", value: (a) => (a.given ? dateWords(a.given) : null) },
    {
      key: "in",
      label: "Papers in",
      width: "8%",
      num: true,
      keep: true,
      value: (a) => `${papersIn(a)} of ${a.copies}`,
      // a class's spare copies, not yet written on, go with its pack: said under the count, apart from it
      cell: (a) => (
        <>
          {papersIn(a)} of {a.copies}
          {a.spares ? <span className="block text-[11.5px] text-basalt/55">and {a.spares} spare</span> : null}
          {a.extras ? <span className="block text-[11.5px] text-basalt/55">and {a.extras} extra</span> : null}
        </>
      ),
    },
    {
      key: "status",
      label: "Status",
      width: "19%",
      status: true,
      keep: true,
      value: (a) => standing(a).state,
      cell: (a) => {
        const s = standing(a);
        return (
          <span data-testid="stage-on-row">
            <StatusChip state={s.state} note={s.note} />
          </span>
        );
      },
    },
  ];
  return (
    <DataTable
      label="Assessments"
      columns={columns}
      rows={views}
      rowKey={assessmentKey}
      more={{ page, href: pageHref }}
      extras={{
        attrs: (a) => ({ "data-assessment": assessmentKey(a) }),
        expand: (a) => {
          const open = copies.get(assessmentKey(a));
          return open ? (
            <div data-copies={assessmentKey(a)}>
              {a.section ? (
                <Link href={cardHref(a)} className="btn secondary mb-2">
                  Open its card →
                </Link>
              ) : null}
              <CopiesTable title={assessmentTitle(a)} rows={open} />
            </div>
          ) : null;
        },
      }}
    />
  );
}
