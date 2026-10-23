// A child's checked answers as a table, and the date format every panel of the child's page uses.
import { mistakeName } from "@/lib/mistake-name";
import { MarkPill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";
import { dateWords } from "@/lib/week";

export const fmtDate = dateWords;

type AnswerRow = Pick<Evidence, "date" | "item_key" | "slot" | "question" | "read" | "answer" | "working" | "status" | "misconception_codes" | "skill_code" | "op"> & {
  id?: string;
  typed?: string | null;
  judged?: string | null;
  mistake_skills?: Record<string, string> | null;
};

const JUDGED: Record<string, string> = { correct: "right", wrong: "wrong", blank: "blank" };

/** What the child wrote, once a person has checked it: what they typed, else the mark they gave it over the reader's
 *  reading, else the reader's own reading, which nobody changed. Never a dash: nothing written is said as nothing. */
function Confirmed({ a }: { a: AnswerRow }) {
  const wrote = a.typed ?? a.read;
  return (
    <>
      {wrote || <span className="text-basalt/62">nothing</span>}
      {a.judged ? <span className="block text-[11.5px] text-basalt/62">you marked it {JUDGED[a.judged] ?? a.judged}</span> : null}
    </>
  );
}

// A child's answers, each once: the evidence behind them is a row for every skill the question tests, so a table that
// lists rows listed a question as many times as it tests skills (goals/dup_answers_listed_twice.yaml). Two columns for
// what the child wrote, told apart: the reader's reading, which a person may have changed, and what they confirmed.
// `signedOff` false: answers not yet checked have only the reader's reading.
export function AnswerTable({ rows, names, signedOff = true }: { rows: AnswerRow[]; names: Record<string, string>; signedOff?: boolean }) {
  const once = rows.filter((a, i) => a.id == null || rows.findIndex((x) => x.id === a.id) === i);
  return (
    <div className="overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            <th>Date</th>
            <th>Q</th>
            <th>Question</th>
            <th className="num">What the reader saw</th>
            {signedOff ? <th className="num">What the child wrote (you confirmed)</th> : null}
            <th className="num">Right answer</th>
            <th className="num">Mark</th>
            <th>Mistake matched</th>
          </tr>
        </thead>
        <tbody>
          {once.map((a, i) => (
            <tr key={a.id ?? i}>
              <td className="fact whitespace-nowrap">{fmtDate(a.date)}</td>
              <td className="fact">{a.slot}</td>
              <td className="max-w-[300px] text-[13px]">
                {a.question}
                {a.working ? <div className="mt-1 text-[12px] text-basalt/55">{a.working}</div> : null}
              </td>
              <td className="num">{a.read || <span className="text-basalt/62">reader saw nothing</span>}</td>
              {signedOff ? (
                <td className="num">
                  <Confirmed a={a} />
                </td>
              ) : null}
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
