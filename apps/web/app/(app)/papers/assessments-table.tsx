import Link from "@/components/link";
import { Pill } from "@/components/shell";
import { classWords } from "@/lib/needs-you";
import { KIND_WORDS, STAGES, STAGE_WORDS, type AssessmentRow } from "@/lib/queries-papers";
import { weekWords } from "@/lib/week";
import { STAGE_TONE } from "./papers-table";

// A class's home assessments or chosen papers for a week are one assessment, named for what they are.
const MANY: Record<string, string> = { focus: "Home assessments", custom: "Chosen papers" };

// By assessment (goals/ui5-assessments-readable.yaml): one row for each assessment, its copies counted at each stage in
// words, the answers waiting for a person, and its score across the copies that are checked; a click anywhere on a row
// opens its copies, one row each, under the same filters.
export function AssessmentsTable({ rows, opens }: { rows: AssessmentRow[]; opens: (a: AssessmentRow) => string }) {
  return (
    <table className="grid" aria-label="Every assessment">
      <thead>
        <tr>
          <th>Assessment</th>
          <th>Kind</th>
          <th className="num">Class</th>
          <th className="num">Week</th>
          <th className="num">Copies</th>
          <th>Where they stand</th>
          <th className="num">Waiting</th>
          <th className="num">Score</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((a) => (
          <tr key={`${a.kind}|${a.section}|${a.week}|${a.set}`} className="relative cursor-pointer hover:bg-basalt/3">
            <td>
              {/* the one link of the row, stretched over all of it: a click anywhere opens its copies */}
              <Link href={opens(a)} className="font-medium text-basalt no-underline after:absolute after:inset-0 after:content-['']">
                {a.set ? a.title : (MANY[a.kind] ?? a.title)}
              </Link>
            </td>
            <td className="whitespace-nowrap">{KIND_WORDS[a.kind] ?? a.kind}</td>
            <td className="num whitespace-nowrap">
              {a.section ? (a.band ? classWords(a.band, a.section) : a.section) : <span className="text-basalt/45">—</span>}
            </td>
            <td className="num fact whitespace-nowrap">{a.week ? weekWords(a.week) : <span className="text-basalt/45">—</span>}</td>
            <td className="num fact whitespace-nowrap">
              {a.copies}
              {a.spares ? <span className="block text-[11.5px] text-basalt/55">and {a.spares} spare</span> : null}
            </td>
            <td>
              <span className="flex flex-wrap gap-1">
                {STAGES.filter((s) => a.by[s]).map((s) => (
                  <Pill key={s} tone={STAGE_TONE[s]}>
                    {a.by[s]} {STAGE_WORDS[s]}
                  </Pill>
                ))}
              </span>
            </td>
            <td className="num">{a.waiting ? a.waiting : <span className="text-basalt/45">—</span>}</td>
            <td className="num whitespace-nowrap">{a.scored ? `${a.right} of ${a.scored}` : <span className="text-basalt/45">—</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
