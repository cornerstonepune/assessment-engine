// A child's checked answers as a table, and the date format every panel of the child's page uses.
import { mistakeName } from "@/lib/mistake-name";
import { MarkPill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";

export const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

type AnswerRow = Pick<Evidence, "date" | "item_key" | "question" | "read" | "answer" | "working" | "status" | "misconception_codes" | "skill_code" | "op"> & {
  id?: string;
  mistake_skills?: Record<string, string> | null;
};

export function AnswerTable({ rows, names }: { rows: AnswerRow[]; names: Record<string, string> }) {
  return (
    <div className="overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            <th>Date</th>
            <th>Q</th>
            <th>Question</th>
            <th className="num">Child wrote</th>
            <th className="num">Key</th>
            <th className="num">Mark</th>
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
              <td className="num">
                <MarkPill status={a.status} working={a.working} />
              </td>
              <td className="text-[12.5px]">{a.misconception_codes.map((c) => mistakeName(names, c, a.op, a.mistake_skills?.[c] ?? a.skill_code)).join("; ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// One glyph per state, in the state's material: a tick, an arrow, a dot, a bang, an empty ring.
