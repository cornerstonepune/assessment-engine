import Link from "@/components/link";
import { Pill } from "@/components/shell";
import { classWords } from "@/lib/needs-you";
import { KIND_WORDS, STAGE_WORDS, type PaperListRow, type Stage } from "@/lib/queries-papers";
import { weekWords } from "@/lib/week";

// A stage's material: what waits on a person reads warm, what is done reads settled (pills never red or green).
export const STAGE_TONE: Record<Stage, "neem" | "bamboo" | "terracotta" | "monsoon"> = {
  made: "monsoon",
  printed: "monsoon",
  scanned: "terracotta",
  checked: "bamboo",
  "signed off": "neem",
};

// Where a paper's work is: its answers once it is read, the page itself before.
const opens = (p: PaperListRow) =>
  p.stage === "made" || p.stage === "printed" ? `/worksheets/${encodeURIComponent(p.qr)}` : `/capture/${p.id}`;

// Each paper (goals/u9-papers.yaml): one row each, a click anywhere on a row opening the paper where its work is.
export function PapersTable({ rows }: { rows: PaperListRow[] }) {
  return (
    <table className="grid" aria-label="Every paper">
      <thead>
        <tr>
          <th>Paper</th>
          <th>Kind</th>
          <th className="num">Class</th>
          <th>Child</th>
          <th className="num">Week</th>
          <th className="num">Stage</th>
          <th className="num">Waiting</th>
          <th className="num">Score</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.id} data-paper={p.id} className="relative cursor-pointer hover:bg-basalt/3">
            <td>
              {/* the one link of the row, stretched over all of it: a click anywhere opens the paper */}
              <Link href={opens(p)} className="font-medium text-basalt no-underline after:absolute after:inset-0 after:content-['']">
                {p.title}
              </Link>
            </td>
            <td className="whitespace-nowrap">{KIND_WORDS[p.kind] ?? p.kind}</td>
            <td className="num whitespace-nowrap">
              {p.section ? (p.band ? classWords(p.band, p.section) : p.section) : <span className="text-basalt/45">—</span>}
            </td>
            <td className="whitespace-nowrap">{p.child ?? <span className="text-basalt/45">spare copy</span>}</td>
            <td className="num fact whitespace-nowrap">{p.week ? weekWords(p.week) : <span className="text-basalt/45">—</span>}</td>
            <td className="num">
              <Pill tone={STAGE_TONE[p.stage]}>{STAGE_WORDS[p.stage]}</Pill>
            </td>
            <td className="num">{p.waiting ? p.waiting : <span className="text-basalt/45">—</span>}</td>
            <td className="num whitespace-nowrap">
              {(p.stage === "checked" || p.stage === "signed off") && p.scored ? (
                `${p.right} of ${p.scored}`
              ) : (
                <span className="text-basalt/45">—</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
