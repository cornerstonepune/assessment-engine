import { notFound } from "next/navigation";
import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { engineSend } from "@/lib/engine";
import { readArea, seeHref, type Area } from "@/lib/next-paper";
import { GRADE_GROUPS, levelsOf, skillSets } from "@/lib/queries";
import { oneChild } from "@/lib/queries-make";
import { isoWeek } from "@/lib/week";
import { approveCustom } from "../actions";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };
type Plan = { areas: { skill_set: string; name: string; level: string; questions: { item_key: string; text: string }[] }[] };

const ROWS = 4; // lines on the form: a paper of up to four skills
const all = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []);

// A paper a teacher chooses for one child (goals/m1-make-papers.yaml): any skills, a level each, how many
// questions. The engine draws them from the bank — none the child has seen — and the teacher sees every question
// before approving; a paper the bank cannot fill is refused in words, never padded.
export default async function CustomPaper({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const id = all(q.child)[0] ?? "";
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const [child, sets] = await deadline(Promise.all([oneChild(id, me.email), skillSets()]));
  if (!child) notFound();

  // The form sends each line as `s` (skill~level) and `n` (how many); a link may carry whole areas as `a`.
  const s = all(q.s);
  const n = all(q.n);
  const areas: Area[] = [
    ...all(q.a).map(readArea),
    ...s.map((v, i) => (v && n[i] ? readArea(`${v}~${n[i]}`) : null)),
  ].filter((a): a is Area => !!a);
  const week = isoWeek();
  let plan: Plan | null = null;
  let refused = "";
  if (areas.length) {
    const res = await engineSend(`/child/${id}/paper/plan`, { week, areas });
    if (res.ok) plan = (await res.json()) as Plan;
    else refused = ((await res.json().catch(() => ({}))) as { detail?: unknown }).detail?.toString() ?? `The engine refused (${res.status}).`;
  }
  const lines = Array.from({ length: ROWS }, (_, i) => areas[i]);
  const grades = [...GRADE_GROUPS].sort(([a], [b]) => Number(b === child.band) - Number(a === child.band));

  return (
    <>
      <PageHeader
        stage="Make papers"
        title={`A paper for ${child.first_name}`}
        sub="Choose up to four skills, a level for each, and how many questions. You see every question before it prints; the child has seen none of them."
      />
      <Body>
        <div className="mb-[18px] flex flex-wrap gap-3">
          <Link href={`/make/${encodeURIComponent(child.section)}`} className="chip">
            ← {child.section} · home papers
          </Link>
          <Link href={`/growth/${id}`} className="chip">
            {child.first_name}&rsquo;s map
          </Link>
        </div>
        <div className="grid gap-[18px] lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
          <Panel title="Choose the paper">
            <form method="get" action="/make/custom" aria-label="Choose the paper" className="grid gap-3">
              <input type="hidden" name="child" value={id} />
              {lines.map((a, i) => (
                <div key={i} className="grid grid-cols-[minmax(0,1fr)_72px] gap-2">
                  <label className="field">
                    <span className="label">Skill and level {i + 1}</span>
                    <select className="select" name="s" defaultValue={a ? `${a.skill_set}~${a.level}` : ""} aria-label={`Skill and level ${i + 1}`}>
                      <option value="">—</option>
                      {grades.map(([band, words]) => {
                        const here = sets.filter((x) => x.band === band);
                        return here.length ? (
                          <optgroup key={band} label={words}>
                            {here.flatMap((x) =>
                              levelsOf(x).map((d) => (
                                <option key={`${x.code}~${d}`} value={`${x.code}~${d}`}>
                                  {x.name} · {d} ({x.counts[d] ?? 0} questions)
                                </option>
                              )),
                            )}
                          </optgroup>
                        ) : null;
                      })}
                    </select>
                  </label>
                  <label className="field">
                    <span className="label">Questions</span>
                    <input className="input" name="n" type="number" min={1} max={40} defaultValue={a?.n ?? ""} aria-label={`Questions ${i + 1}`} />
                  </label>
                </div>
              ))}
              <button className="btn self-start" type="submit">
                See the paper
              </button>
            </form>
          </Panel>

          <section aria-label="The paper">
            <Panel title="The paper" aside={plan ? `${plan.areas.reduce((t, a) => t + a.questions.length, 0)} questions` : undefined}>
              {refused ? <Notice tone="terracotta">{refused}</Notice> : null}
              {plan ? (
                <>
                  {plan.areas.map((a) => (
                    <div key={`${a.skill_set}~${a.level}`} className="mb-4">
                      <h3 className="mb-1 text-[14px]">
                        {a.name} · {a.level}
                      </h3>
                      <ol aria-label={`${a.name} · ${a.level}`} className="grid list-decimal gap-1 pl-5 text-[13px]">
                        {a.questions.map((x) => (
                          <li key={x.item_key}>{x.text}</li>
                        ))}
                      </ol>
                    </div>
                  ))}
                  <form action={approveCustom}>
                    <input type="hidden" name="child" value={id} />
                    <input type="hidden" name="week" value={week} />
                    {areas.map((a) => (
                      <input key={`${a.skill_set}~${a.level}`} type="hidden" name="a" value={`${a.skill_set}~${a.level}~${a.n}`} />
                    ))}
                    <button className="btn" type="submit">
                      Approve and print
                    </button>{" "}
                    <a href={seeHref(id, week, areas)} target="_blank" rel="noreferrer" className="ml-3">
                      See it as it will print
                    </a>
                  </form>
                </>
              ) : !refused ? (
                <p className="note">Choose at least one skill and how many questions, then see the paper.</p>
              ) : null}
            </Panel>
          </section>
        </div>
      </Body>
    </>
  );
}
