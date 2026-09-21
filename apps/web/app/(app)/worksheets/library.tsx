import Link from "@/components/link";
import { KIND } from "@/components/question";
import { Panel } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { DIFFICULTIES, skillSets } from "@/lib/queries";
import { worksheetCount, worksheets } from "@/lib/queries-worksheets";

const PER_PAGE = 50;

/** "3 column sums · 3 word problems" — what a worksheet holds, by kind, in words. */
export function kindsInWords(kinds: Record<string, number> | null): string {
  return Object.entries(kinds ?? {})
    .map(([fmt, n]) => `${n} ${KIND[fmt] ?? fmt}`)
    .join(" · ");
}

type Q = Record<string, string | undefined>;

// Every question in the bank is on a numbered worksheet (ADR 0026). The grid is every skill at every
// level with its worksheets; a count opens that list, and a worksheet opens its own page.
export async function Library({ q }: { q: Q }) {
  const filter = { set: q.set, level: DIFFICULTIES.find((d) => d === q.level) };
  const page = Math.max(1, Number(q.page) || 1);
  const [sets, rows, total] = await deadline(
    Promise.all([skillSets(), worksheets(filter, PER_PAGE, (page - 1) * PER_PAGE), worksheetCount(filter)]),
  );
  const all = sets.reduce((n, s) => n + Object.values(s.worksheets).reduce((a, b) => a + (b ?? 0), 0), 0);
  const link = (p: Q) => {
    const next = new URLSearchParams(
      Object.entries({ set: filter.set, level: filter.level, ...p }).filter(([, v]) => v) as [string, string][],
    );
    return `/worksheets?${next}#library`;
  };
  const shown = filter.set ? sets.find((s) => s.code === filter.set)?.name : undefined;

  return (
    <section id="library" className="scroll-mt-6">
      <Panel
        title="Worksheet library"
        aside={`${all.toLocaleString("en-IN")} worksheets · every question in the bank is on one`}
      >
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
                {DIFFICULTIES.map((d) => (
                  <th key={d} className="text-right">
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
                  {DIFFICULTIES.map((d) => (
                    <td key={d} className="num">
                      <Link
                        href={link({ set: s.code, level: d, page: undefined })}
                        aria-label={`${s.name}, ${d}: ${s.worksheets[d] ?? 0} worksheets`}
                      >
                        {s.worksheets[d] ?? 0}
                      </Link>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-[18px] flex flex-wrap items-center gap-2" aria-label="Show worksheets for">
          <Link href={link({ level: undefined, page: undefined })} className={`chip ${filter.level ? "" : "on"}`}>
            Every level
          </Link>
          {DIFFICULTIES.map((d) => (
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
              href={`/worksheets?${new URLSearchParams(filter.level ? { level: filter.level } : {})}#library`}
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
                <th>Level</th>
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
                  <td>{w.difficulty}</td>
                  <td className="text-[12.5px] text-basalt/70">{kindsInWords(w.kinds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note mt-3 flex flex-wrap gap-4">
          <span>
            {total
              ? `${(page - 1) * PER_PAGE + 1}–${Math.min(page * PER_PAGE, total)} of ${total}`
              : "No worksheets here yet."}
          </span>
          {page > 1 ? <Link href={link({ page: String(page - 1) })}>← Previous {PER_PAGE}</Link> : null}
          {page * PER_PAGE < total ? <Link href={link({ page: String(page + 1) })}>Next {PER_PAGE} →</Link> : null}
        </p>
      </Panel>
    </section>
  );
}
