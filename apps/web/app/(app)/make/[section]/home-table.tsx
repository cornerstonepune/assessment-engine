import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import { Questions } from "@/components/questions";
import { seeHref } from "@/lib/next-paper";
import type { ClassChild } from "@/lib/queries-make";
import type { Column } from "@/lib/ux-rules";
import { approveHome } from "../actions";

export type HomeRow = { child: ClassChild; state: State; approvedBy: string | null; draw: number };

const ORDER: Record<string, number> = { chooseOne: 0, toApprove: 1, done: 2 };
/** The educator first: a child with nothing to go on, then those waiting for approval, then the approved. */
export const byNeed = (a: HomeRow, b: HomeRow) => (ORDER[a.state] ?? 9) - (ORDER[b.state] ?? 9);

// A class's children and their home assessment this week as one table (goals/uxn5-print-and-give.yaml): the one skill the
// engine proposes and why, where it stands, and the one next step. The paper's questions are on its line before anything
// prints; "Different questions" draws others for that child alone, making nothing (goals/preview-before-print.yaml).
export function HomeTable({ rows, week, section, draws, differentFor, page, pageHref, each }: {
  rows: HomeRow[]; week: string; section: string; draws: Record<string, number>; differentFor: (id: string) => string;
  page: number; pageHref: (n: number) => string; each: number | null;
}) {
  const custom = (id: string) => `/make/custom?child=${id}`;
  const cols: Column<HomeRow>[] = [
    { key: "roll", label: "Roll", num: true, width: "3.5rem", value: (r) => r.child.roll_no },
    { key: "who", label: "Child", width: "6.5rem", value: (r) => r.child.first_name, cell: (r) => <Link href={`/growth/${r.child.id}`}>{r.child.first_name}</Link> },
    {
      key: "works",
      label: "Works on",
      width: "14rem",
      value: (r) => r.child.proposal.areas[0]?.name ?? (r.state === "done" ? "approved" : "Not enough checked work yet"),
      cell: (r) => {
        const a = r.child.proposal.areas[0];
        const done = r.child.proposal.approved;
        if (r.state === "done" && done) {
          return (
            <>
              <Link href={`/worksheets/${done.qr}`} className="fact">{done.qr}</Link>
              {done.replaced.length ? <span className="note"> · replaces {done.replaced.join(", ")}</span> : null}
            </>
          );
        }
        if (!a) return <span className="text-basalt/62">Not enough checked work yet</span>;
        return (
          <>
            <a href={seeHref(r.child.id, week, [], draws[r.child.id] ?? 0)} target="_blank" rel="noreferrer">
              {a.name} · {a.level}
              {each ? null : ` · ${a.questions.length} questions`}
            </a>
            <details className="mt-1">
              <summary className="cursor-pointer text-[13px]">Its questions</summary>
              <Questions name={a.name} level={a.level} questions={a.questions} />
            </details>
          </>
        );
      },
    },
    { key: "why", label: "Why", value: (r) => (r.state === "done" ? "" : r.child.proposal.areas[0]?.why), cell: (r) => <span className="text-[12.5px] text-basalt/75">{r.state === "done" ? null : r.child.proposal.areas[0]?.why}</span> },
    {
      key: "state",
      label: "Status",
      status: true,
      width: "9rem",
      value: (r) => r.state,
      cell: (r) => <StatusChip state={r.state} words={r.state === "done" ? "approved" : undefined} note={r.state === "done" && r.approvedBy ? `by ${r.approvedBy}` : undefined} />,
    },
    {
      key: "next",
      label: "Next step",
      width: "10rem",
      keep: true,
      value: (r) => r.state,
      cell: (r) => {
        const a = r.child.proposal.areas[0];
        if (r.state === "done") {
          // made again as often as an educator likes: the newest is the week's (goals/home-assessment-remake.yaml)
          return <Link href={`/growth/${r.child.id}`}>Make a new one</Link>;
        }
        if (!a) return <Link href={custom(r.child.id)}>Choose one</Link>;
        return (
          <>
            <form action={approveHome}>
              <input type="hidden" name="week" value={week} />
              <input type="hidden" name="section" value={section} />
              <input type="hidden" name="child_id" value={r.child.id} />
              <input type="hidden" name="draw" value={draws[r.child.id] ?? 0} />
              <input type="hidden" name="seen" value={r.child.proposal.seen} />
              <button className="cursor-pointer font-semibold text-terracotta underline-offset-2 hover:underline" type="submit">
                Approve
              </button>
            </form>
            <Link href={differentFor(r.child.id)} className="mt-1 block text-[12.5px]">
              Different questions
            </Link>
            <Link href={custom(r.child.id)} className="mt-1 block text-[12.5px]">
              or choose another
            </Link>
          </>
        );
      },
    },
  ];
  return (
    <DataTable
      label="Each child's home assessment"
      columns={cols}
      rows={rows}
      rowKey={(r) => r.child.id}
      more={{ page, href: pageHref }}
      extras={{ attrs: (r) => ({ "data-child": r.child.id }) }}
    />
  );
}
