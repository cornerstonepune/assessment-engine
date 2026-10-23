import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import { levels } from "@/lib/levels";
import { RULE_WORDS } from "@/lib/queries";
import type { Column } from "@/lib/ux-rules";
import { LIBRARY_CODE, sheetWords } from "../../worksheets/[qr]/library-sheet";
import { overrideChild } from "./actions";

// One line of a class's pack: a child's paper, a child with none (and why), or a spare with no name on it.
export type PackRow = {
  key: string;
  roll: string;
  who: string;
  level: string | null;
  why: string;
  qr: string | null;
  worksheet: string | null;
  state: State;
  /** The child's plan, when their level may be changed. */
  prescription: string | null;
  difficulty: string | null;
};

const ORDER: Record<string, number> = { noPaper: 0, toApprove: 1, done: 2 };
/** What needs the educator first: a child with no paper, then papers to approve, then what is approved. */
export const byNeed = (a: PackRow, b: PackRow) => (ORDER[a.state] ?? 9) - (ORDER[b.state] ?? 9);

export const reasonOf = (r: { rule_fired: string; override_by: string | null; override_reason: string | null }) =>
  `${RULE_WORDS[r.rule_fired] ?? r.rule_fired}${r.override_reason ? ` ${r.override_by}: ${r.override_reason}` : ""}`;

// The class's pack as one table (goals/uxn4-papers-to-approve.yaml): who, the level and why, the paper, where it stands.
export async function PackTable({ rows, back, page, pageHref }: { rows: PackRow[]; back: string; page: number; pageHref: (n: number) => string }) {
  const { order } = await levels();
  const columns: Column<PackRow>[] = [
    { key: "roll", label: "Roll", num: true, width: "4.5rem", value: (r) => r.roll },
    { key: "who", label: "Child", width: "9rem", value: (r) => r.who, cell: (r) => (r.roll ? <Link href={`/growth/${r.key}`} className="font-medium">{r.who}</Link> : <span className="font-medium">{r.who}</span>) },
    { key: "level", label: "Level", width: "7rem", value: (r) => r.level },
    { key: "why", label: "Why", value: (r) => r.why, cell: (r) => <span className="text-[13px] text-basalt/75">{r.why}</span> },
    {
      key: "paper",
      label: "Paper",
      width: "13rem",
      value: (r) => r.qr,
      cell: (r) =>
        r.qr ? (
          <span className="fact whitespace-nowrap">
            {/* the paper by what it is, its printed code only to match a page in hand (goals/ux8b-papers-named.yaml) */}
            <Link href={`/worksheets/${r.qr}`}>See the paper</Link>
            {r.worksheet ? (
              <>
                {" · "}
                {LIBRARY_CODE.test(r.worksheet) ? <Link href={`/worksheets/${r.worksheet}`}>{sheetWords(r.worksheet)}</Link> : r.worksheet}
              </>
            ) : null}
            <span className="block text-[11.5px] text-basalt/55">printed code {r.qr}</span>
          </span>
        ) : null,
    },
    { key: "state", label: "Status", status: true, width: "10rem", value: (r) => r.state, cell: (r) => <StatusChip state={r.state} words={r.state === "done" ? "approved" : undefined} /> },
    {
      key: "change",
      label: "",
      width: "9rem",
      keep: true,
      value: (r) => r.prescription,
      cell: (r) =>
        r.prescription ? (
          <details className="max-md:w-full">
            <summary className="cursor-pointer whitespace-nowrap text-[13px] text-terracotta">Change level</summary>
            <form action={overrideChild} className="mt-2 grid w-full gap-2 md:w-[230px]">
              <input type="hidden" name="prescription_id" value={r.prescription} />
              <input type="hidden" name="back" value={back} />
              <label className="field">
                <span className="label">New level</span>
                <select className="select" name="difficulty" defaultValue={r.difficulty ?? undefined}>
                  {order.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="label">Why</span>
                <input className="input" name="reason" maxLength={300} required />
              </label>
              <button className="btn secondary" type="submit">
                Change this child
              </button>
            </form>
          </details>
        ) : null,
    },
  ];
  return (
    <DataTable
      label="Each child's paper this week"
      columns={columns}
      rows={rows}
      rowKey={(r) => r.key}
      more={{ page, href: pageHref }}
      extras={{ attrs: (r) => (r.prescription ? { "data-child": r.key } : ({} as Record<string, string>)) }}
    />
  );
}
