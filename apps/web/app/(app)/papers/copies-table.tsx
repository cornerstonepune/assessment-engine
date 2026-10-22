import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import { STAGE_WORDS, type PaperListRow, type Stage } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";

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

const COLUMNS: Column<PaperListRow>[] = [
  { key: "roll", label: "Roll", width: "5rem", num: true, value: (p) => p.roll_no },
  {
    key: "child",
    label: "Child",
    value: (p) => p.child ?? "spare copy",
    cell: (p) => (
      <Link href={opens(p)} className="font-medium">
        {p.child ?? "spare copy"}
      </Link>
    ),
  },
  { key: "level", label: "Level", width: "7rem", value: (p) => p.level },
  { key: "stage", label: "Stage", width: "13rem", status: true, keep: true, value: (p) => STAGE_WORDS[p.stage], cell: (p) => <StatusChip state={STAGE_STATE[p.stage]} /> },
  { key: "waiting", label: "Waiting", width: "6rem", num: true, value: (p) => p.waiting },
  {
    key: "score",
    label: "Score",
    width: "7rem",
    num: true,
    value: (p) => ((p.stage === "checked" || p.stage === "signed off") && p.scored ? `${p.right} of ${p.scored}` : null),
  },
];

// An assessment's copies (goals/ux5-papers-grouped.yaml): one row each in roll order, its child opening the paper where
// its work is; the spares, not yet written on, one line under them — they go with the pack and wait for no one. A class
// is one table, up to forty children: the copies of one assessment are read together, never paged.
export function CopiesTable({ title, rows }: { title: string; rows: PaperListRow[] }) {
  const copies = rows.filter((p) => !p.spare);
  const spares = rows.filter((p) => p.spare);
  return (
    <div className="pb-2">
      {copies.length ? (
        <DataTable label={`${title}: each copy`} columns={COLUMNS} rows={copies} rowKey={(p) => p.id} more={{ page: 1, href: () => "" }} limit={40} extras={{ attrs: (p) => ({ "data-paper": p.id }) }} />
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
