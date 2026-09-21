import Link from "next/link";
import { notFound } from "next/navigation";
import { Answers, KIND, mistakeOf, printsItsWording } from "@/components/question";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { mistakeBook, questionPage, type QuestionPage } from "@/lib/queries-bank";
import { correctItem, flagItem } from "../actions";

type Props = {
  params: Promise<{ key: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
};

// One question, everything about it: how it prints, its answer, every wrong answer it catches and
// what each one means, where it came from — and the two things a person can do to it.
export default async function QuestionScreen({ params, searchParams }: Props) {
  const [{ key }, q] = await Promise.all([params, searchParams]);
  if (!/^[A-Za-z0-9._-]+$/.test(key)) notFound();
  const [it, book] = await Promise.all([questionPage(key), mistakeBook()]);
  if (!it) notFound();

  const live = it.status === "active";
  const kind = KIND[it.fmt] ?? it.fmt;
  const caught = it.responses.flatMap((r) =>
    Object.entries(r.misconceptions ?? {}).map(([code, wrong]) => ({ code, wrong, mistake: mistakeOf(book, code, it.spec.op) })),
  );

  return (
    <>
      <PageHeader
        stage="Stage 2 · The bank"
        title={kind.charAt(0).toUpperCase() + kind.slice(1)}
        sub={`${it.skill_set_name} · ${it.difficulty}`}
      />
      <Body>
        <Link href={`/library?set=${it.skill_set_code}&difficulty=${it.difficulty}#questions`} className="mb-4 inline-block text-[13px]">
          ← All {it.difficulty} questions in {it.skill_set_name}
        </Link>
        {q.corrected ? <Notice tone="neem">Saved. This is the corrected question; the old wording will not print again.</Notice> : null}
        {q.error ? <Notice tone="terracotta">{q.error}</Notice> : null}
        {live ? null : (
          <Notice tone="terracotta">
            Removed{it.removed_by ? ` by ${it.removed_by}` : ""}
            {it.removed_note ? ` — ${it.removed_note}` : ""}. It will not print again.{" "}
            {it.replaced_by_key ? <Link href={`/library/${it.replaced_by_key}`}>Open the corrected question →</Link> : null}
          </Notice>
        )}

        <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="grid content-start gap-[18px]">
            <Panel title="As it prints">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/question/${it.item_key}`}
                alt="The question as it prints on a paper"
                className="w-full max-w-[760px] border border-basalt/14 bg-white"
              />
            </Panel>

            <Panel title="Answer">
              <Answers it={it} rubric />
            </Panel>

            <Panel title="Wrong answers it catches" aside={String(caught.length)}>
              {caught.length ? (
                <div className="overflow-x-auto">
                  <table className="grid" aria-label="Wrong answers it catches">
                    <thead>
                      <tr>
                        <th className="text-right">If the child writes</th>
                        <th>The mistake</th>
                        <th>What it looks like</th>
                      </tr>
                    </thead>
                    <tbody>
                      {caught.map(({ code, wrong, mistake }, i) => (
                        <tr key={`${code}-${i}`}>
                          <td className="num">{wrong}</td>
                          <td className="min-w-[160px]">
                            {mistake?.name ?? <span className="fact text-[11px]">{code}</span>}
                          </td>
                          <td className="min-w-[200px] text-[12.5px] text-basalt/70">{mistake?.description ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="note">This question is judged by a person, so there is no list of wrong answers.</p>
              )}
            </Panel>
          </div>

          <div className="grid content-start gap-[18px]">
            <Panel title="About it">
              <dl className="grid gap-3 text-[13.5px]">
                <Fact label="Skill set">
                  <Link href={`/skill-sets/${it.skill_set_code}`}>{it.skill_set_name}</Link>
                </Fact>
                <Fact label="Level">
                  {it.difficulty}
                  {it.level_words ? <span className="note block">{it.level_words}</span> : null}
                </Fact>
                <Fact label="Made by">{madeBy(it)}</Fact>
                <Fact label="On papers">{it.children ? `${it.children} children have had it` : "Not on a paper yet"}</Fact>
              </dl>
            </Panel>

            {live && printsItsWording(it.fmt) ? (
              <Panel title="Correct the wording">
                <form action={correctItem} className="grid gap-3">
                  <input type="hidden" name="item_key" value={it.item_key} />
                  <label className="field">
                    <span className="label">Wording</span>
                    <textarea className="textarea min-h-[110px]" name="stem" defaultValue={it.stem} maxLength={600} required />
                  </label>
                  <label className="field">
                    <span className="label">What was wrong</span>
                    <input className="input" name="reason" maxLength={300} required />
                  </label>
                  <p className="note">Keep the numbers as they are, so the answer cannot change.</p>
                  <button className="btn" type="submit">
                    Save correction
                  </button>
                </form>
              </Panel>
            ) : null}

            {live ? (
              <Panel title="Remove">
                <form action={flagItem} className="grid gap-3">
                  <input type="hidden" name="item_key" value={it.item_key} />
                  <input type="hidden" name="back" value={`/library/${it.item_key}`} />
                  <label className="field">
                    <span className="label">Why remove it</span>
                    <input className="input" name="note" maxLength={300} required />
                  </label>
                  <button className="btn secondary" type="submit">
                    Remove this question
                  </button>
                </form>
              </Panel>
            ) : null}
          </div>
        </div>
      </Body>
    </>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="label mb-[3px]">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function madeBy(it: QuestionPage) {
  if (it.generator === "correction") {
    return (
      <>
        Reworded by a teacher
        {it.corrected_from_key ? (
          <span className="note block">
            <Link href={`/library/${it.corrected_from_key}`}>See the original wording</Link>
          </span>
        ) : null}
      </>
    );
  }
  return `The engine, from this level's rule${it.skill_set_version ? ` (version ${it.skill_set_version})` : ""}`;
}
