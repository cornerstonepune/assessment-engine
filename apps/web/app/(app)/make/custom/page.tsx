import { notFound } from "next/navigation";
import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { NotYours } from "@/components/not-yours";
import { childSection, isMine, scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { engineSend } from "@/lib/engine";
import { readArea, seeHref, type Area } from "@/lib/next-paper";
import { lineTopics, repeatWords } from "@/lib/maker";
import { grades, skillSets } from "@/lib/queries";
import { oneChild } from "@/lib/queries-make";
import { isoWeek } from "@/lib/week";
import { approveCustom } from "../actions";
import { MakerLines } from "../lines";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };
type Plan = { areas: { skill_set: string; name: string; level: string; seen_before: number; questions: { item_key: string; text: string }[] }[] };

const ROWS = 4; // lines on the form: a paper of up to four skills
const all = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []);

// A paper a teacher chooses for one child (goals/m1-make-papers.yaml): any skills, a level each, how many
// questions, each line a topic first (ADR 0081). The engine draws them from the bank — first those the child was not
// given lately, then those given longest ago (ADR 0080) — and the teacher sees every question before approving.
export default async function CustomPaper({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const id = all(q.child)[0] ?? "";
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const section = await deadline(childSection(id));
  if (!isMine(scopeOf(me), section)) return <NotYours what="This child's class" />;
  // every skill, each saying whether the child's class was taught it: the educator's choice decides (ADR 0081)
  const [child, sets, g] = await deadline(
    Promise.all([oneChild(id, me.email), skillSets({ untaught: true, section: section ?? "" }), grades()]),
  );
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

  return (
    <>
      <PageHeader
        stage="Assessments · make"
        title={`A home assessment for ${child.first_name}`}
        sub="Choose up to four skills, a level for each, and how many questions. You see every question before it prints; the child has seen none of them."
      />
      <Body>
        <div className="mb-[18px] flex flex-wrap gap-3">
          <Link href={`/make/${encodeURIComponent(child.section)}`} className="chip">
            ← {child.section} · home assessments
          </Link>
          <Link href={`/growth/${id}`} className="chip">
            {child.first_name}&rsquo;s map
          </Link>
        </div>
        <div className="grid gap-[18px] lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
          <Panel title="Choose the paper">
            <form method="get" action="/make/custom" aria-label="Choose the paper" className="grid gap-3">
              <input type="hidden" name="child" value={id} />
              <MakerLines
                key={lines.map((a) => (a ? `${a.skill_set}~${a.level}~${a.n}` : "")).join("|")}
                topics={lineTopics(g, sets, child.band, null, ROWS)}
                start={lines.map((a) => (a ? `${a.skill_set}~${a.level}~${a.n}` : ""))}
              />
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
                  {repeatWords(plan.areas) ? <p className="note mb-3">{repeatWords(plan.areas)}</p> : null}
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
