// A child's checked answers as a table, and the date format every panel of the child's page uses.
import { MarkPill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";

export const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

type AnswerRow = Pick<Evidence, "date" | "item_key" | "question" | "read" | "answer" | "working" | "status" | "misconception_codes"> & { id?: string };

export function AnswerTable({ rows, names }: { rows: AnswerRow[]; names: Record<string, string> }) {
  return (
    <div className="overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            <th>Date</th>
            <th>Q</th>
            <th>Question</th>
            <th className="text-right">Child wrote</th>
            <th className="text-right">Key</th>
            <th>Mark</th>
            <th>Mistake matched</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a, i) => (
            <tr key={a.id ?? i}>
              <td className="fact whitespace-nowrap">{fmtDate(a.date)}</td>
              <td className="fact">{a.item_key.split("/").pop()}</td>
              <td className="max-w-[300px] text-[13px]">
                {a.question}
                {a.working ? <div className="mt-1 text-[12px] text-basalt/55">{a.working}</div> : null}
              </td>
              <td className="num">{a.read || "—"}</td>
              <td className="num">{a.answer ?? "—"}</td>
              <td>
                <MarkPill status={a.status} working={a.working} />
              </td>
              <td className="text-[12.5px]">{a.misconception_codes.map((c) => names[c] ?? c).join("; ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// One glyph per state, in the state's material: a tick, an arrow, a dot, a bang, an empty ring.
