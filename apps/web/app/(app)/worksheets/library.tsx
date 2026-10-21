import Link from "@/components/link";
import { KIND } from "@/components/question";
import { Panel } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { levels } from "@/lib/levels";
import { gradeOf, grades, skillSets } from "@/lib/queries";
import { gradesOf, type Scope } from "@/lib/scope";
import { libraryTotal, worksheetCount, worksheets } from "@/lib/queries-worksheets";

const PER_PAGE = 50;

/** "3 column sums · 3 word problems" — what a worksheet holds, by kind, in words. */
export function kindsInWords(kinds: Record<string, number> | null): string {
  return Object.entries(kinds ?? {})
    .map(([fmt, n]) => `${n} ${KIND[fmt] ?? fmt}`)
    .join(" · ");
}

type Q = Record<string, string | undefined>;

// Every question in the bank is on a numbered worksheet (ADR 0026). The grid is every taught skill at every level with its
// worksheets; a count opens that list, and a worksheet opens its own page. It opens on the person's own grade, its levels
// alone, every grade one tap away (goals/ux6-curriculum-for-the-educator.yaml).
export async function Library({ q, scope }: { q: Q; scope: Scope }) {
  const [{ order }, mine, g] = await deadline(Promise.all([levels(), gradesOf(scope), grades()]));
  const inGrades = q.grade === "all" ? [] : mine;
  const gradeWords = inGrades.map((b) => g.name(b)).join(" and ");
  const filter = { set: q.set, level: order.find((d) => d === q.level), scope, grades: inGrades };
  const page = Math.max(1, Number(q.page) || 1);
  const [taught, rows, total, library] = await deadline(
    Promise.all([skillSets({ scope }), worksheets(filter, PER_PAGE, (page - 1) * PER_PAGE), worksheetCount(filter), libraryTotal()]),
  );
  // a level of another grade is a dash, and a skill with no level of the grade shown is not a row
  const ofGrade = (s: (typeof taught)[number], d: string) => !inGrades.length || inGrades.includes(gradeOf(s, d));
  const sets = taught.filter((s) => order.some((d) => ofGrade(s, d) && s.worksheets[d]));
  const all = sets.reduce((n, s) => n + order.reduce((a, d) => a + (ofGrade(s, d) ? (s.worksheets[d] ?? 0) : 0), 0), 0);
  const link = (p: Q) => {
    const next = new URLSearchParams(
      Object.entries({ set: filter.set, level: filter.level, grade: q.grade, ...p }).filter(([, v]) => v) as [string, string][],
    );
    return `/worksheets?${next}#library`;
  };
  const shown = filter.set ? sets.find((s) => s.code === filter.set)?.name : undefined;

  return (
    <section id="library" className="scroll-mt-6">
      <Panel
        title={gradeWords ? `Worksheet library · ${gradeWords}` : "Worksheet library"}
        aside={`${all.toLocaleString("en-IN")} worksheets of the skills taught${gradeWords ? ` in ${gradeWords}` : ""}, of the library's ${library.toLocaleString("en-IN")} · every question in the bank is on one`}
      >
        <p className="mb-3">
          <Link href="/worksheets/taxonomy" className="chip">
            See the worksheets by taxonomy case →
          </Link>
        </p>
        <p className="note mb-4">
          Twelve questions of one skill at one level on each worksheet, the level&rsquo;s kinds of question mixed in
          fair shares. A level with too few different questions for ten worksheets shares its questions across them,
          each used equally often.
        </p>
        <div className="overflow-x-auto">
          <table className="grid" aria-label="Worksheets by skill and level">
            <thead>
              <tr>
                <th>What the child can do</th>
                {order.map((d) => (
                  <th key={d} className="num">
                    {d}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sets.map((s) => (
                <tr key={s.code}>
                  <td className="min-w-[280px] max-w-[520px] text-[13px]">
                    <Link href={`/skill-sets/${s.code}#worksheets`} className="text-basalt">
                      {s.learning_objective}
                    </Link>
                  </td>
                  {order.map((d) => (
                    <td key={d} className="num">
                      {ofGrade(s, d) ? (
                        <Link
                          href={link({ set: s.code, level: d, page: undefined })}
                          aria-label={`${s.name}, ${d}: ${s.worksheets[d] ?? 0} worksheets`}
                        >
                          {s.worksheets[d] ?? 0}
                        </Link>
                      ) : (
                        <span className="text-basalt/35">—</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {mine.length ? (
          <div className="mt-[18px] flex flex-wrap items-center gap-2" aria-label="Show worksheets of">
            <Link href={link({ grade: undefined, page: undefined })} className={`chip ${q.grade === "all" ? "" : "on"}`}>
              {mine.map((b) => g.name(b)).join(" and ")}
            </Link>
            <Link href={link({ grade: "all", page: undefined })} className={`chip ${q.grade === "all" ? "on" : ""}`}>
              Every grade
            </Link>
          </div>
        ) : null}
        <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Show worksheets for">
          <Link href={link({ level: undefined, page: undefined })} className={`chip ${filter.level ? "" : "on"}`}>
            Every level
          </Link>
          {order.map((d) => (
            <Link
              key={d}
              href={link({ level: d, page: undefined })}
              className={`chip ${filter.level === d ? "on" : ""}`}
            >
              {d}
            </Link>
          ))}
          {filter.set ? (
            <Link
              href={link({ set: undefined, page: undefined })}
              className="chip"
            >
              {shown} ✕
            </Link>
          ) : null}
        </div>

        <div className="mt-3 overflow-x-auto">
          <table className="grid" aria-label="Worksheets">
            <thead>
              <tr>
                <th>Worksheet</th>
                <th>Skill</th>
                <th className="num">Level</th>
                <th>Its twelve questions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((w) => (
                <tr key={w.code}>
                  <td className="fact whitespace-nowrap">
                    <Link href={`/worksheets/${w.code}`}>{w.code}</Link>
                  </td>
                  <td className="min-w-[180px]">{w.skill}</td>
                  <td className="num">{w.difficulty}</td>
                  <td className="text-[12.5px] text-basalt/70">{kindsInWords(w.kinds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note mt-3 flex flex-wrap gap-4">
          <span>
            {total
              ? `${(page - 1) * PER_PAGE + 1}–${Math.min(page * PER_PAGE, total)} of ${total.toLocaleString("en-IN")}`
              : "No worksheets here yet."}
          </span>
          {page > 1 ? <Link href={link({ page: String(page - 1) })}>← Previous {PER_PAGE}</Link> : null}
          {page * PER_PAGE < total ? <Link href={link({ page: String(page + 1) })}>Next {PER_PAGE} →</Link> : null}
        </p>
      </Panel>
    </section>
  );
}
