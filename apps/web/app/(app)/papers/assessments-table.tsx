import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { actionOf, standingWords, stepCells, type Action, type Cell } from "@/lib/assessment-steps";
import { KIND_WORDS, type AssessmentRow, type PaperListRow } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";
import { dateWords, weekWords } from "@/lib/week";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { approveRow, renameAssessment } from "./actions";
import { CopiesTable } from "./copies-table";
import { countsOf, stepColumns } from "./step-columns";

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

export const assessmentTitle = (a: Pick<AssessmentRow, "set" | "kind" | "title">) => (a.set ? a.title : (MANY[a.kind] ?? a.title));

export type Named = AssessmentRow & {
  /** The name shown: an educator's, else built from the sheet. */
  name: string;
  /** The files read whose codes belong to it, by their own names. */
  files: string[];
  gradeWords: string | null;
  /** A file read that belongs to no assessment: it is its own row. */
  ghost?: string;
};

type Go = { href: string } | { form: "approve" } | { none: string };
const where = (a: Named, act: Action): Go => {
  switch (act.kind) {
    case "approve":
      return { form: "approve" };
    case "print":
    case "results":
      return { href: cardHref(a) };
    case "upload":
      return { href: "/papers#read-box" };
    case "reading":
      return { href: "/capture" };
    case "check":
      return { href: "/capture/check" };
    case "signoff":
      return { href: a.signId ? `/capture/${a.signId}` : cardHref(a) };
    default:
      return { none: act.label };
  }
};

function ActionCell({ a, back }: { a: Named; back: string }) {
  if (a.ghost) return <Link href="/capture" className="btn secondary whitespace-nowrap">Look at the file</Link>;
  const counts = countsOf(a);
  const act = actionOf(counts, a.waiting);
  const go = where(a, act);
  return (
    <div className="grid w-full justify-items-end gap-1">
      {"form" in go ? (
        <form action={approveRow}>
          <input type="hidden" name="section" value={a.section ?? ""} />
          <input type="hidden" name="week" value={a.week ?? ""} />
          <input type="hidden" name="back" value={back} />
          <button type="submit" className="btn secondary" data-action="approve">
            {act.label}
          </button>
        </form>
      ) : "href" in go ? (
        <Link href={go.href} className="btn secondary" data-action={act.kind}>
          {act.label}
        </Link>
      ) : (
        <span className="text-[12.5px] text-basalt/65">{go.none}</span>
      )}
      <span data-testid="stage-on-row" className="text-right text-[11.5px] text-basalt/60">
        {standingWords(counts, a.waiting)}
      </span>
    </div>
  );
}

function NameCell({ a, open, href, back }: { a: Named; open: boolean; href: string; back: string }) {
  if (a.ghost)
    return (
      <>
        <span className="font-medium text-terracotta" data-unmatched>
          Not matched to an assessment
        </span>
        <span className="block text-[11.5px] text-basalt/60">file: {a.ghost}</span>
      </>
    );
  const key = assessmentKey(a);
  return (
    <>
      {/* the marker is drawn, not written: the line's words are the assessment's alone */}
      <Link
        href={href}
        aria-expanded={open}
        className={`font-medium text-basalt before:mr-1 before:inline-block before:w-3 before:text-basalt/50 ${open ? "before:content-['▾']" : "before:content-['▸']"}`}
      >
        {a.name}
      </Link>
      {a.week ? <span className="block pl-4 text-[11.5px] text-basalt/60">{weekWords(a.week)}</span> : null}
      {a.files.length ? (
        <span className="block pl-4 text-[11.5px] text-basalt/60" data-files>
          file: {a.files.slice(0, 2).join(", ")}
          {a.files.length > 2 ? ` and ${a.files.length - 2} more` : ""}
        </span>
      ) : null}
      <details className="pl-4 text-[12px]">
        <summary className="cursor-pointer text-basalt/60">Rename</summary>
        <form action={renameAssessment} className="mt-1 flex gap-1">
          <input type="hidden" name="key" value={key} />
          <input type="hidden" name="back" value={back} />
          <input name="name" defaultValue={a.name} maxLength={120} aria-label="Name this assessment" className="input min-w-0 flex-1 !py-1 !text-[13px]" />
          <button type="submit" className="btn secondary !px-2 !py-1 !text-[12px]">
            Save
          </button>
        </form>
      </details>
    </>
  );
}

// The last assessments, one row each, newest first (goals/asm_assessments_page.yaml): its name — the educator's, else built
// from the sheet's own code — its kind, class and day, the steps it has been through in the order the school does them,
// the score, and the one thing to do next. A row opens to its children, each with the same steps and their own pages.
export async function AssessmentsTable({
  rows,
  copies,
  pages,
  page,
  back,
  href,
  pageHref,
}: {
  rows: Named[];
  copies: Map<string, PaperListRow[]>;
  pages: Map<string, { capture: string; pages: number[] }>;
  page: number;
  /** The list as it is addressed now, so a rename or an approval comes back to it. */
  back: string;
  href: (a: Named, open: boolean) => string;
  pageHref: (page: number) => string;
}) {
  const g = await grades();
  const cells = (a: Named): Cell[] => (a.ghost ? [] : stepCells(countsOf(a), a.waiting).cells);
  const columns: Column<Named>[] = [
    {
      key: "name",
      label: "Assessment",
      width: "15%",
      keep: true,
      value: (a) => a.name,
      cell: (a) => <NameCell a={a} open={copies.has(assessmentKey(a))} href={href(a, copies.has(assessmentKey(a)))} back={back} />,
    },
    { key: "kind", label: "Kind", width: "8.5%", value: (a) => (a.ghost ? null : (KIND_WORDS[a.kind] ?? a.kind)) },
    { key: "class", label: "Class", width: "8%", value: (a) => (a.ghost || !a.section ? null : a.band ? classWords(g, a.band, a.section) : a.section) },
    { key: "made", label: "Made on", width: "7%", value: (a) => (a.day ? dateWords(a.day.slice(0, 10)) : null) },
    ...stepColumns<Named>(cells),
    {
      key: "score",
      label: "Score",
      width: "5.5%",
      num: true,
      value: (a) => (a.scored ? `${a.right} of ${a.scored}` : null),
    },
    { key: "action", label: "Next", width: "14%", keep: true, value: () => "action", cell: (a) => <ActionCell a={a} back={back} /> },
  ];
  return (
    <DataTable
      label="Assessments"
      dense
      columns={columns}
      rows={rows}
      rowKey={(a) => (a.ghost ? `file~${a.ghost}` : assessmentKey(a))}
      more={{ page, href: pageHref }}
      extras={{
        attrs: (a): Record<string, string> => (a.ghost ? { "data-unmatched-file": a.ghost } : { "data-assessment": assessmentKey(a) }),
        expand: (a) => {
          const open = copies.get(assessmentKey(a));
          return open && !a.ghost ? (
            <div data-copies={assessmentKey(a)}>
              <Link href={cardHref(a)} className="btn secondary mb-2">
                Open its card →
              </Link>
              <CopiesTable title={assessmentTitle(a)} rows={open} pages={pages} />
            </div>
          ) : null;
        },
      }}
    />
  );
}
