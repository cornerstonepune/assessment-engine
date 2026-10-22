import Link from "@/components/link";
import { Answers, kindWords, Question } from "@/components/question";
import { questionKinds } from "@/lib/question-types";
import { Body, PageHeader, Panel } from "@/components/shell";
import { levels } from "@/lib/levels";
import { bankGrid, bankTotals, itemCount, items } from "@/lib/queries-bank";
import { deadline } from "@/lib/deadline";
import { Proposals } from "./proposals";
import { requireStaff } from "@/lib/auth";
import { gradesOf, scopeOf } from "@/lib/scope";
import { gradeOf, grades } from "@/lib/queries";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const PER_PAGE = 50;
const n = (x: number) => x.toLocaleString("en-IN");

export default async function LibraryPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const find = q.find?.trim().slice(0, 80) || undefined;
  // the questions of what the person's classes have been taught (goals/f1f-taught-per-class.yaml)
  const scope = scopeOf(me);
  // it opens on the person's own grade, every grade one tap away; the coordinator's on every grade
  // (goals/ux6-curriculum-for-the-educator.yaml)
  const [mine, g] = await deadline(Promise.all([gradesOf(scope), grades()]));
  const shown = q.grade === "all" ? [] : mine;
  const gradeWords = shown.map((b) => g.name(b)).join(" and ");
  const filter = { set: q.set, difficulty: q.difficulty, fmt: q.fmt, status: q.status, find, scope, grades: shown };
  const page = Math.max(1, Math.trunc(Number(q.page)) || 1);
  const [grid, totals, total, rows, { order }, { words }] = await deadline(Promise.all([
    bankGrid(scope),
    bankTotals(scope),
    itemCount(filter),
    items(filter, PER_PAGE, (page - 1) * PER_PAGE),
    levels(),
    questionKinds(),
  ]));
  // the stock — each level's count, the removed, every grade's skills — is the coordinator's; an educator reads one count
  // per skill, of the levels of the grade shown
  const stock = me.role === "coordinator";
  const ofGrade = (r: (typeof grid)[number]) => order.filter((d) => !shown.length || shown.includes(gradeOf(r, d)));
  const mineGrid = grid
    .map((r) => ({ ...r, n: ofGrade(r).reduce((a, d) => a + (r.counts[d] ?? 0), 0), at: ofGrade(r) }))
    .filter((r) => r.at.length && r.n);
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
        stage="Curriculum · Question bank"
        title="Question bank"
        sub={`${n(totals.active)} questions ready to print for the skills taught, of the bank's ${n(totals.bank)}; every one is on a numbered worksheet.`}
      />
      <Body>
        <Panel title="What the bank is">
          <div className="grid max-w-[820px] gap-2 text-[14px] leading-relaxed">
            <p>
              The question bank is every question the engine has made and checked: {n(totals.bank)} today, at{" "}
              {order.slice(0, -1).join(", ")} and {order.at(-1)}. {n(totals.active)} of them are of the {grid.length} skills taught in a class, the ones a
              child can be given now; they are the ones below.
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
        {q.error ? (
          <p role="alert" className="mb-3 text-[14px]">
            {q.error}
          </p>
        ) : null}
        <Proposals />
        <div className="h-[18px]" />
        {stock ? null : (
          <Panel title={`What is in the bank${gradeWords ? ` for ${gradeWords}` : ""}`} aside={`${n(mineGrid.reduce((a, r) => a + r.n, 0))} ready, of the skills taught${scope.classes ? " in your classes" : ""}`}>
            {/* Curriculum counts every skill of a grade, taught or not, so the two totals differ (goals/ux8c-one-word.yaml) */}
            <p className="note mb-3">Only skills taught are counted here; Curriculum counts every skill of the grade, taught or not.</p>
            <div className="overflow-x-auto">
              <table className="grid" aria-label={`${gradeWords || "Every grade"}: questions by skill`}>
                <thead>
                  <tr>
                    <th>Skill</th>
                    <th>Kinds of question</th>
                    <th className="num">Questions</th>
                  </tr>
                </thead>
                <tbody>
                  {mineGrid.map((r) => (
                    <tr key={r.code} className={r.code === q.set ? "bg-bamboo/12" : undefined}>
                      <td className="min-w-[180px]">
                        <Link href={link({ set: r.code, difficulty: undefined, fmt: undefined })}>{r.name}</Link>
                      </td>
                      <td className="text-[12px] text-basalt/62">{r.fmts.map((f) => kindWords(words, f)).join(" · ")}</td>
                      <td className="num">{n(r.n)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        )}
        {stock ? (
          <Panel title="What is in the bank" aside={`${n(totals.active)} ready · ${n(totals.retired)} removed`}>
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Questions by skill set and level">
                <thead>
                  <tr>
                    <th>Skill set</th>
                    <th className="num">Grade</th>
                    <th>Kinds of question</th>
                    {order.map((d) => (
                      <th key={d} className="num">
                        {d}
                      </th>
                    ))}
                    <th className="num">All</th>
                  </tr>
                </thead>
                <tbody>
                  {grid.map((r) => (
                    <tr key={r.code} className={r.code === q.set ? "bg-bamboo/12" : undefined}>
                      <td className="min-w-[220px]">
                        <Link href={link({ set: r.code, difficulty: undefined, fmt: undefined })}>{r.name}</Link>
                      </td>
                      <td className="num whitespace-nowrap">{g.name(r.band)}</td>
                      <td className="min-w-[180px] text-[12px] text-basalt/62">
                        {r.fmts.map((f) => kindWords(words, f)).join(" · ")}
                      </td>
                      {order.map((d) => {
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
                      <td className="num">{n(order.reduce((a, d) => a + (r.counts[d] ?? 0), 0))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="note mt-3">
              Each paper is drawn from one cell. <Link href="/worksheets">See a real paper with its QR code →</Link>
            </p>
          </Panel>
        ) : null}

        <section id="questions" className="mt-[18px] scroll-mt-4">
          <Panel
            label="Questions"
            title={`${chosen ? `${chosen.name}${q.difficulty ? ` · ${q.difficulty}` : ""}` : gradeWords ? `${gradeWords}'s questions` : "Every question"}${find ? `, with “${find}”` : ""}`}
            aside={
              total
                ? `${n((page - 1) * PER_PAGE + 1)}–${n(Math.min(page * PER_PAGE, total))} of ${n(total)}`
                : "none"
            }
          >
            {/* a question found by its words, within the choices already made: they ride along as hidden fields */}
            <form role="search" aria-label="Find a question" action="/library#questions" className="mb-4 flex flex-wrap items-end gap-2">
              {(["set", "difficulty", "fmt", "status", "grade"] as const).map((k) =>
                q[k] ? <input key={k} type="hidden" name={k} value={q[k]} /> : null,
              )}
              <label className="field min-w-[260px] flex-1">
                <span className="label">Words or numbers in the question</span>
                <input className="input" type="search" name="find" defaultValue={find ?? ""} maxLength={80} />
              </label>
              <button className="btn" type="submit">
                Find
              </button>
            </form>
            {mine.length ? (
              <div className="mb-3 flex flex-wrap gap-2">
                {chip("grade", undefined, mine.map((b) => g.name(b)).join(" and "))}
                {chip("grade", "all", "Every grade")}
              </div>
            ) : null}
            <div className="mb-3 flex flex-wrap gap-2">
              {chip("difficulty", undefined, "Any level")}
              {order.map((d) => chip("difficulty", d, d))}
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              {chip("fmt", undefined, "Any kind")}
              {kinds
                .map((f) => [f, kindWords(words, f)])
                .sort((a, b) => a[1].localeCompare(b[1]))
                .map(([f, w]) => chip("fmt", f, w))}
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {chip("status", undefined, "Ready to print")}
              {chip("status", "retired", "Removed")}
              {q.set || q.difficulty || q.fmt || q.status || find ? (
                <Link href="/library#questions" className="ml-2 text-[12.5px]">
                  Clear all choices
                </Link>
              ) : null}
            </div>

            {rows.length === 0 ? (
              <p className="note">No questions match these choices. Try other words, or another level or kind.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Answer</th>
                      <th>Kind</th>
                      <th>Worksheets</th>
                      <th className="num"></th>
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
                        <td className="min-w-[110px] text-[12.5px]">{kindWords(words, it.fmt)}</td>
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
                        <td className="num">
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
