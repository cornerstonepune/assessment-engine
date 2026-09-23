import Link from "@/components/link";
import { Answers, KIND, Question } from "@/components/question";
import { Body, PageHeader, Panel } from "@/components/shell";
import { DIFFICULTIES } from "@/lib/queries";
import { bankGrid, bankTotals, itemCount, items } from "@/lib/queries-bank";
import { deadline } from "@/lib/deadline";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const PER_PAGE = 50;
const n = (x: number) => x.toLocaleString("en-IN");

export default async function LibraryPage({ searchParams }: Props) {
  const q = await searchParams;
  const filter = { set: q.set, difficulty: q.difficulty, fmt: q.fmt, status: q.status };
  const page = Math.max(1, Math.trunc(Number(q.page)) || 1);
  const [grid, totals, total, rows] = await deadline(Promise.all([
    bankGrid(),
    bankTotals(),
    itemCount(filter),
    items(filter, PER_PAGE, (page - 1) * PER_PAGE),
  ]));
  const pages = Math.max(1, Math.ceil(total / PER_PAGE));
  const chosen = grid.find((r) => r.code === q.set);
  const kinds = chosen?.fmts ?? [...new Set(grid.flatMap((r) => r.fmts))];

  // Every choice is a link: the URL is the state, so a view can be bookmarked or sent to a colleague.
  const link = (changes: Record<string, string | undefined>) => {
    const merged: Record<string, string | undefined> = { ...q, page: undefined, ...changes };
    const s = new URLSearchParams(Object.entries(merged).filter((e): e is [string, string] => !!e[1])).toString();
    return `/library${s ? `?${s}` : ""}#questions`;
  };
  // Where a question came from, saying only what the choices above do not already fix.
  const caption = (it: { skill_set_name: string | null; difficulty: string | null }) =>
    [chosen ? null : it.skill_set_name, q.difficulty ? null : it.difficulty].filter(Boolean).join(" · ");
  const chip = (k: string, v: string | undefined, label: string) => (
    <Chip key={`${k}-${v ?? ""}`} href={link({ [k]: v })} on={(q[k] ?? "") === (v ?? "")} label={label} />
  );

  return (
    <>
      <PageHeader
        stage="Stage 2 · The bank"
        title="Question bank"
        sub={`${n(totals.active)} questions ready to print, every one of them on a numbered worksheet.`}
      />
      <Body>
        <Panel title="What the bank is">
          <div className="grid max-w-[820px] gap-2 text-[14px] leading-relaxed">
            <p>
              The question bank is every question the engine can put in front of a child: {n(totals.active)} today, for the{" "}
              {grid.length} skills in the Curriculum, at Easy, Medium, Hard and Advance.
            </p>
            <p>
              The engine makes each question from its skill&rsquo;s own rule for that level, and a computer checks every
              answer — and every wrong answer a mistake would produce — before the question is kept. Any member of staff can
              reword a question or remove it.
            </p>
            <p>
              Every question belongs to one skill and one level, is one kind — a column sum, a word problem, a number wall
              — and sits on at least one numbered worksheet. Each question below shows those ties; open one to see it as it
              prints, with every wrong answer it can catch.
            </p>
          </div>
        </Panel>
        <div className="h-[18px]" />
        <Panel title="What is in the bank" aside={`${n(totals.active)} ready · ${n(totals.retired)} removed`}>
          <div className="overflow-x-auto">
            <table className="grid" aria-label="Questions by skill set and level">
              <thead>
                <tr>
                  <th>Skill set</th>
                  <th>Grade</th>
                  <th>Kinds of question</th>
                  {DIFFICULTIES.map((d) => (
                    <th key={d} className="text-right">
                      {d}
                    </th>
                  ))}
                  <th className="text-right">All</th>
                </tr>
              </thead>
              <tbody>
                {grid.map((r) => (
                  <tr key={r.code} className={r.code === q.set ? "bg-bamboo/12" : undefined}>
                    <td className="min-w-[220px]">
                      <Link href={link({ set: r.code, difficulty: undefined, fmt: undefined })}>{r.name}</Link>
                    </td>
                    <td className="fact">{r.band}</td>
                    <td className="min-w-[180px] text-[12px] text-basalt/62">
                      {r.fmts.map((f) => KIND[f] ?? f).join(" · ")}
                    </td>
                    {DIFFICULTIES.map((d) => {
                      const on = r.code === q.set && d === q.difficulty;
                      return (
                        <td key={d} className="num">
                          <Link
                            href={link({ set: r.code, difficulty: d, fmt: undefined })}
                            aria-label={`${r.name}, ${d}: ${r.counts[d] ?? 0} questions`}
                            className={on ? "font-semibold text-terracotta" : undefined}
                          >
                            {n(r.counts[d] ?? 0)}
                          </Link>
                        </td>
                      );
                    })}
                    <td className="num">{n(DIFFICULTIES.reduce((a, d) => a + (r.counts[d] ?? 0), 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note mt-3">
            Each paper is drawn from one cell. <Link href="/worksheets">See a real paper with its QR code →</Link>
          </p>
        </Panel>

        <section id="questions" className="mt-[18px] scroll-mt-4">
          <Panel
            title={chosen ? `${chosen.name}${q.difficulty ? ` · ${q.difficulty}` : ""}` : "Every question"}
            aside={
              total
                ? `${n((page - 1) * PER_PAGE + 1)}–${n(Math.min(page * PER_PAGE, total))} of ${n(total)}`
                : "none"
            }
          >
            <div className="mb-3 flex flex-wrap gap-2">
              {chip("difficulty", undefined, "Any level")}
              {DIFFICULTIES.map((d) => chip("difficulty", d, d))}
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              {chip("fmt", undefined, "Any kind")}
              {Object.keys(KIND)
                .filter((f) => kinds.includes(f))
                .map((f) => chip("fmt", f, KIND[f]))}
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {chip("status", undefined, "Ready to print")}
              {chip("status", "retired", "Removed")}
              {q.set || q.difficulty || q.fmt || q.status ? (
                <Link href="/library#questions" className="ml-2 text-[12.5px]">
                  Clear all choices
                </Link>
              ) : null}
            </div>

            {rows.length === 0 ? (
              <p className="note">No questions match these choices. Try another level or kind.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Answer</th>
                      <th>Kind</th>
                      <th>Worksheets</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((it) => (
                      <tr key={it.item_key}>
                        <td className="min-w-[240px] max-w-[460px]">
                          <Link href={`/library/${it.item_key}`} className="block text-basalt hover:text-terracotta">
                            <Question it={it} />
                          </Link>
                          {caption(it) ? <span className="note mt-[6px] block">{caption(it)}</span> : null}
                        </td>
                        <td>
                          <Answers it={it} />
                        </td>
                        <td className="min-w-[110px] text-[12.5px]">{KIND[it.fmt] ?? it.fmt}</td>
                        <td className="text-[12.5px]">
                          {it.worksheets.length ? (
                            <span className="flex flex-wrap gap-x-2">
                              {it.worksheets.map((c) => (
                                <Link key={c} href={`/worksheets/${c}`} className="fact whitespace-nowrap">
                                  {c}
                                </Link>
                              ))}
                            </span>
                          ) : (
                            <span className="note">none</span>
                          )}
                        </td>
                        <td className="text-right">
                          <Link href={`/library/${it.item_key}`} className="whitespace-nowrap text-[12.5px]" tabIndex={-1} aria-hidden>
                            Open →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {pages > 1 ? (
              <nav className="mt-4 flex flex-wrap items-center gap-4 text-[13px]" aria-label="Pages of questions">
                {page > 1 ? <Link href={link({ page: String(page - 1) })}>← Previous {PER_PAGE}</Link> : null}
                <span className="fact text-basalt/55">
                  page {n(page)} of {n(pages)}
                </span>
                {page < pages ? <Link href={link({ page: String(page + 1) })}>Next {PER_PAGE} →</Link> : null}
              </nav>
            ) : null}
          </Panel>
        </section>
      </Body>
    </>
  );
}

function Chip({ href, on, label }: { href: string; on: boolean; label: string }) {
  return (
    <Link href={href} className={`chip ${on ? "on" : ""}`}>
      {label}
    </Link>
  );
}
