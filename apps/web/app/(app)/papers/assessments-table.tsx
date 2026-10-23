import Link from "@/components/link";
import { Pill } from "@/components/shell";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { KIND_WORDS, STAGES, STAGE_WORDS, type AssessmentRow, type PaperListRow } from "@/lib/queries-papers";
import { CopiesTable, STAGE_TONE } from "./copies-table";

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

// A week's assessments (goals/ui5-assessments-readable.yaml, goals/ux5-papers-grouped.yaml): one line each — what it is,
// its class, its copies counted at each stage in words, the answers waiting for a person, its score across the copies
// that are checked — its name opening it in place to its copies (`copies`, by assessment), and closing it again.
export async function AssessmentsTable({
  label,
  rows,
  copies,
  href,
}: {
  label: string;
  rows: AssessmentRow[];
  copies: Map<string, PaperListRow[]>;
  href: (a: AssessmentRow, open: boolean) => string;
}) {
  const g = await grades();
  return (
    <table className="grid" aria-label={label}>
      <thead>
        <tr>
          <th>Assessment</th>
          {/* on a phone where an assessment stands sits beside its name: the columns the row's own copies repeat fold away
              (goals/ux8d-phone-and-one-action.yaml) */}
          <th className="max-md:hidden">Kind</th>
          <th className="max-md:hidden">Class</th>
          <th className="num max-md:hidden">Copies</th>
          <th>Where they stand</th>
          <th className="num">Waiting</th>
          <th className="num max-md:hidden">Score</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((a) => {
          const key = assessmentKey(a);
          const open = copies.get(key);
          return [
            <tr key={key} data-assessment={key} className={open ? "bg-basalt/3" : undefined}>
              <td>
                {/* the marker is drawn, not written: the line's words are the assessment's alone */}
                <Link
                  href={href(a, !!open)}
                  aria-expanded={!!open}
                  className={`font-medium text-basalt before:mr-1 before:inline-block before:w-3 before:text-basalt/50 ${open ? "before:content-['▾']" : "before:content-['▸']"}`}
                >
                  {assessmentTitle(a)}
                </Link>
              </td>
              <td className="whitespace-nowrap max-md:hidden">{KIND_WORDS[a.kind] ?? a.kind}</td>
              <td className="whitespace-nowrap max-md:hidden">
                {a.section ? (a.band ? classWords(g, a.band, a.section) : a.section) : <span className="text-basalt/45">—</span>}
              </td>
              <td className="num fact whitespace-nowrap max-md:hidden">
                {a.copies}
                {a.spares ? <span className="block text-[11.5px] text-basalt/55">and {a.spares} spare</span> : null}
                {a.extras ? <span className="block text-[11.5px] text-basalt/55">and {a.extras} extra</span> : null}
              </td>
              <td>
                <span data-testid="stage-on-row" className="flex flex-wrap gap-1">
                  {STAGES.filter((s) => a.by[s]).map((s) => (
                    <Pill key={s} tone={STAGE_TONE[s]}>
                      {a.by[s]} {STAGE_WORDS[s]}
                    </Pill>
                  ))}
                </span>
              </td>
              <td className="num">{a.waiting ? a.waiting : <span className="text-basalt/45">—</span>}</td>
              <td className="num whitespace-nowrap max-md:hidden">{a.scored ? `${a.right} of ${a.scored}` : <span className="text-basalt/45">—</span>}</td>
            </tr>,
            open ? (
              <tr key={`${key}|copies`} data-copies={key}>
                <td colSpan={7} className="!pl-8">
                  {a.section ? (
                    <Link href={cardHref(a)} className="btn secondary mb-2">
                      Open its card →
                    </Link>
                  ) : null}
                  <CopiesTable title={assessmentTitle(a)} rows={open} />
                </td>
              </tr>
            ) : null,
          ];
        })}
      </tbody>
    </table>
  );
}
