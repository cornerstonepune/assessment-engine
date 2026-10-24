import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import type { State } from "@/components/status-chip";
import { actionOf, stepCells } from "@/lib/assessment-steps";
import type { PaperListRow, Stage } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";
import { countsOfPaper, stepColumns } from "./step-columns";

// A stage as a state of the one chip: what waits on a person is red, what waits on something else amber, done is green.
export const STAGE_STATE: Record<Stage, State> = {
  made: "toApprove",
  printed: "withChildren",
  scanned: "toCheck",
  checked: "toSignOff",
  "signed off": "done",
  replaced: "replaced",
};

// Where a paper's work is: its answers once it is read, the page itself before.
export const opens = (p: PaperListRow) =>
  p.stage === "made" || p.stage === "printed" || p.stage === "replaced" ? `/worksheets/${encodeURIComponent(p.qr)}` : `/capture/${p.id}`;

const isScored = (p: PaperListRow) => (p.stage === "checked" || p.stage === "signed off") && !!p.scored;

/** Where a child's one action goes: the paper itself to print, the checking screen, the child's page of answers. */
const goesTo = (p: PaperListRow, kind: string) =>
  kind === "print" ? `/worksheets/${encodeURIComponent(p.qr)}` : kind === "upload" ? "/papers#read-box" : kind === "check" ? "/capture/check" : `/capture/${p.id}`;

type Pages = Map<string, { capture: string; pages: number[] }>;

function columns(pages: Pages): Column<PaperListRow>[] {
  return [
    { key: "roll", label: "Roll", width: "5%", num: true, value: (p) => p.roll_no },
    {
      key: "child",
      label: "Child",
      width: "14%",
      value: (p) => p.child ?? "spare copy",
      cell: (p) => (
        <Link href={opens(p)} className="font-medium">
          {p.child ?? "spare copy"}
        </Link>
      ),
    },
    { key: "level", label: "Level", width: "7%", value: (p) => p.level },
    ...stepColumns<PaperListRow>((p) => stepCells(countsOfPaper(p), p.waiting).cells),
    {
      key: "score",
      label: "Score",
      width: "7%",
      num: true,
      value: (p) => (isScored(p) ? `${p.right} of ${p.scored}` : null),
      // a paper with nothing right is probably the wrong page: said under the score (goals/dup_answers_listed_twice.yaml)
      cell: (p) => (
        <>
          {isScored(p) ? `${p.right} of ${p.scored}` : null}
          {isScored(p) && !p.right ? (
            <span data-warn className="block text-[11.5px] text-terracotta">
              {p.blank === p.scored ? "every answer blank" : "none right"}: is this the right page?
            </span>
          ) : null}
        </>
      ),
    },
    {
      key: "pages",
      label: "Next",
      width: "14%",
      keep: true,
      value: () => "pages",
      cell: (p) => {
        const act = actionOf(countsOfPaper(p), p.waiting);
        const mine = pages.get(p.id);
        return (
          <div className="grid justify-items-end gap-1">
            {act.kind === "approve" ? (
              <span className="text-[12px] text-basalt/65">approved with its row</span>
            ) : act.kind === "none" ? (
              <span className="text-[12px] text-basalt/65">replaced by a newer one</span>
            ) : (
              <Link href={goesTo(p, act.kind)} className="btn secondary whitespace-nowrap" data-action={act.kind}>
                {act.label}
              </Link>
            )}
            {mine ? (
              <details className="text-[12px]" data-pages={p.id}>
                <summary className="cursor-pointer text-basalt/70">Open pages ({mine.pages.length})</summary>
                <div className="mt-1 flex gap-1">
                  {mine.pages.map((n) => (
                    <Link key={n} href={`/capture/${p.id}`} aria-label={`Page ${n} of ${p.child ?? "this"} paper`}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={`/api/scan/${mine.capture}/${n}`} alt={`Page ${n}`} loading="lazy" className="h-24 w-auto border border-basalt/20" />
                    </Link>
                  ))}
                </div>
              </details>
            ) : null}
          </div>
        );
      },
    },
  ];
}

// An assessment's copies (goals/ux5-papers-grouped.yaml): one row each in roll order, its child opening the paper where
// its work is; the spares, not yet written on, one line under them — they go with the pack and wait for no one. A class
// is one table, up to forty children: the copies of one assessment are read together, never paged.
export function CopiesTable({ title, rows, pages }: { title: string; rows: PaperListRow[]; pages: Pages }) {
  const copies = rows.filter((p) => !p.spare && !p.extra);
  const spares = rows.filter((p) => p.spare);
  const extras = rows.filter((p) => p.extra);
  return (
    <div className="pb-2">
      {copies.length ? (
        <DataTable dense label={`${title}: each copy`} columns={columns(pages)} rows={copies} rowKey={(p) => p.id} more={{ page: 1, href: () => "" }} limit={40} extras={{ attrs: (p) => ({ "data-paper": p.id }) }} />
      ) : null}
      {extras.length ? (
        <p data-extras className="mt-2 text-[12.5px] text-basalt/70">
          {extras.length} extra {extras.length === 1 ? "copy" : "copies"} of {extras.length === 1 ? "a child" : "children"} who {extras.length === 1 ? "has" : "have"}{" "}
          already handed theirs in, not read:{" "}
          {extras.map((p, i) => (
            <span key={p.id}>
              <Link href={opens(p)} className="fact">
                {p.qr}
              </Link>
              {i < extras.length - 1 ? ", " : ""}
            </span>
          ))}
        </p>
      ) : null}
      {spares.length ? (
        <p data-spares className="mt-2 text-[12.5px] text-basalt/70">
          {spares.length} spare {spares.length === 1 ? "copy" : "copies"}, with the pack:{" "}
          {spares.map((p, i) => (
            <span key={p.id}>
              <Link href={opens(p)} className="fact">
                {p.qr}
              </Link>
              {i < spares.length - 1 ? ", " : ""}
            </span>
          ))}
        </p>
      ) : null}
    </div>
  );
}
