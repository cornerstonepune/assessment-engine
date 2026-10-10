// The pieces every Marking view shares (goals/u3-marking.yaml): where a group of papers' answers stand, a table of
// papers, and how the reader is doing. The counts are the engine's (answer_standing); nothing here decides one.
import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import type { PaperRow, ReaderReport } from "@/lib/queries-read";
import { ReaderTable } from "./reader-table";

export const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

/** A group of papers — a class, a child, a worksheet, everything — and where the answers on them stand. */
export type Standing = {
  papers: number;
  answers: number;
  engine: number;
  person: number;
  waiting: number;
  signed: number;
  toSign: number;
  answersToSign: number;
};

export function standing(rows: PaperRow[]): Standing {
  const read = rows.filter((p) => p.n_results > 0);
  return {
    papers: read.length,
    answers: rows.reduce((n, p) => n + p.n_results, 0),
    engine: rows.reduce((n, p) => n + p.n_engine, 0),
    person: rows.reduce((n, p) => n + p.n_person, 0),
    waiting: rows.reduce((n, p) => n + p.n_waiting, 0),
    signed: read.filter((p) => p.n_candidate === 0).length,
    toSign: read.filter((p) => p.n_candidate > 0).length,
    answersToSign: read.reduce((n, p) => n + p.n_candidate, 0),
  };
}

/** The same numbers as table cells, labelled for a test to read. Every answer read is settled by the engine, checked
 *  by a person or still waiting, so the three after "Answers read" add up to it. */
export function StandingCells({ s }: { s: Standing }) {
  return (
    <>
      <td className="num" data-testid="papers">{s.papers}</td>
      <td className="num" data-testid="answers">{s.answers}</td>
      <td className="num" data-testid="engine">{s.engine}</td>
      <td className="num" data-testid="person">{s.person}</td>
      <td className="num" data-testid="waiting">{s.waiting ? <Pill tone="bamboo">{s.waiting}</Pill> : "—"}</td>
      <td className="num whitespace-nowrap text-[12.5px]">
        {s.papers === 0 ? "—" : s.signed === s.papers ? <Pill tone="neem">all {s.papers} signed off</Pill> : `${s.signed} of ${s.papers} signed off`}
      </td>
    </>
  );
}

export const STANDING_HEADS = (
  <>
    <th className="num">Papers in</th>
    <th className="num">Answers read</th>
    <th className="num">Settled by the engine</th>
    <th className="num">Checked by a person</th>
    <th className="num">Still waiting</th>
    <th className="num">Signed off</th>
  </>
);

/** The row under a table that adds its rows up: every paper and answer in it, so the columns visibly sum. `span` is
 *  how many columns come before the numbers (the name, and a count of children when the table has one). */
export function TotalRow({ rows, span, kids }: { rows: PaperRow[]; span: number; kids?: number }) {
  return (
    <tfoot>
      <tr aria-label="Total" className="font-semibold">
        <td colSpan={kids === undefined ? span : span - 1}>Total</td>
        {kids === undefined ? null : <td className="num">{kids}</td>}
        <StandingCells s={standing(rows)} />
      </tr>
    </tfoot>
  );
}

/** One kind of number in the top row: a count and its words, the count labelled for a test to read. */
export function Count({ id, n, words, tone }: { id: string; n: number; words: string; tone: "neem" | "bamboo" | "terracotta" | "monsoon" }) {
  const edge = { neem: "border-l-neem", bamboo: "border-l-bamboo", terracotta: "border-l-terracotta", monsoon: "border-l-monsoon" }[tone];
  return (
    <div className={`panel border-l-4 p-3 ${edge}`}>
      <div className="font-heading text-[26px] leading-none" data-testid={id}>{n}</div>
      <div className="mt-2 text-[12.5px] text-basalt/62">{words}</div>
    </div>
  );
}

export function PaperTable({ rows, withChild = false }: { rows: PaperRow[]; withChild?: boolean }) {
  return (
    <div className="min-w-0 overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            {withChild ? <th>Child</th> : null}
            <th>Paper</th>
            <th className="num">Sat</th>
            <th className="num">Answers</th>
            <th className="num">By the engine</th>
            <th className="num">By a person</th>
            <th className="num">Waiting</th>
            <th className="num">Score</th>
            <th className="num">State</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              {withChild ? (
                <td>
                  <Link href={`/capture?child=${p.child_id}`}>{p.first_name}</Link>
                  <div className="text-[12px] text-basalt/55">{p.section}</div>
                </td>
              ) : null}
              <td className="max-w-[280px] text-[13px]">
                <Link href={`/capture/${p.id}`}>{p.title ?? p.paper}</Link>
              </td>
              <td className="num fact whitespace-nowrap">{fmtDate(p.date)}</td>
              <td className="num">{p.n_results}</td>
              <td className="num">{p.n_engine}</td>
              <td className="num">{p.n_person}</td>
              <td className="num">{p.n_waiting || "—"}</td>
              <td className="num whitespace-nowrap">
                {/* A score once nothing on the sheet waits for a person: right, of every answer that counts. */}
                {p.n_results > 0 && p.n_flagged === 0 ? `${p.n_right} / ${p.n_scored} right` : "—"}
              </td>
              <td className="num whitespace-nowrap">
                {p.n_results === 0 ? (
                  <Pill tone="terracotta">nothing read</Pill>
                ) : p.n_candidate === 0 ? (
                  <Pill tone="neem">signed off</Pill>
                ) : p.n_flagged > 0 ? (
                  <Pill tone="bamboo">{p.n_flagged} need your eyes</Pill>
                ) : (
                  <Pill tone="monsoon">read, not signed off</Pill>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Every check teaches the reader about that child (ADR 0032); this says what the checks so far add up to, so the effort
// can be seen to pay, and whether the reader is getting better: one table, by day first (`ReaderTable`).
const pct = (a: number, b: number) => (b ? `${Math.round((100 * a) / b)}%` : "—");

export function ReaderPanel({ r }: { r: ReaderReport }) {
  const read = r.days.filter((d) => d.stood_behind > 0); // newest first
  const [latest, first] = [read[0], read[read.length - 1]];
  return (
    <Panel title="How the reader is doing" label="How the reader is doing" aside={`from ${r.checked} answers people have checked`}>
      <p className="text-[15px] leading-snug">
        Checked by a person: {r.checked} answers. The reader was right on {r.right} of the {r.stood_behind} it stood behind ({pct(r.right, r.stood_behind)}),
        wrong on {r.stood_behind - r.right}, and gave up on {r.gave_up}{r.gave_up ? ` (its guess was right on ${r.guess_right})` : ""}.
        {first && latest && first !== latest
          ? ` On the first papers it read (${fmtDate(first.day)}) it was right on ${pct(first.right, first.stood_behind)}; on the latest (${fmtDate(latest.day)}), ${pct(latest.right, latest.stood_behind)}.`
          : ""}{" "}
        Every check you make teaches it how that child writes; a kind of question is settled by the reader alone only once it has matched you{" "}
        {Math.round(r.bar * 100)}% of the time over the last {r.window} checks. By kind of question says how many more right checks each still needs.
      </p>
      {r.days.length || r.kinds.length || r.bands.length ? <ReaderTable r={r} /> : null}
    </Panel>
  );
}
