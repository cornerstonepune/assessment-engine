// The child's next paper, chosen from their own ladder (goals/s11-focus-paper.yaml, u2-children.yaml). The engine
// proposes (`w2_print/focus_paper.py`): this reads its plan and shows it in plain words — which areas, why, the
// questions — and a teacher approves it with one button, which prints it in their name. Once a week: an approved
// paper is shown with who approved it, and no second one is offered.
import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import { EngineDown, engineGet } from "@/lib/engine";
import { isoWeek } from "@/lib/week";
import { approveNextPaper } from "../actions";
import { fmtDate } from "./graph";

type Question = { item_key: string; text: string; fmt: string; shows_mistake: boolean };
type Area = { skill_set: string; name: string; level: string; right: number; answered: number; why: string; questions: Question[] };
type Approved = { qr: string; approved_by: string | null; approved_at: string | null };
type Plan = { week: string; areas: Area[]; n: number; approved: Approved | null };

async function plan(childId: string, week: string): Promise<Plan | string> {
  try {
    const res = await engineGet(`/child/${childId}/focus?week=${week}`);
    return res.ok ? ((await res.json()) as Plan) : `The engine could not make the plan (${res.status}).`;
  } catch (e) {
    return e instanceof EngineDown ? e.message : "The engine could not make the plan.";
  }
}

const TITLE = "Next paper, proposed by the engine";

export async function FocusPanel({ childId, name, staff }: { childId: string; name: string; staff: Record<string, string> }) {
  const week = isoWeek();
  const p = await plan(childId, week);
  return (
    <section aria-label={TITLE}>
    <Panel title={TITLE} aside={typeof p === "string" || p.approved ? undefined : `${p.n} questions`}>
      {typeof p === "string" ? (
        <p className="note">{p}</p>
      ) : p.approved ? (
        <p className="text-[13.5px]">
          Approved by {staff[p.approved.approved_by ?? ""] ?? p.approved.approved_by}
          {p.approved.approved_at ? ` on ${fmtDate(p.approved.approved_at)}` : ""}: this week&rsquo;s paper,{" "}
          <Link href={`/worksheets/${p.approved.qr}`}>{p.approved.qr}</Link>. Print it from its page; the next proposal
          comes next week, from what this one shows.
        </p>
      ) : p.areas.length === 0 ? (
        <p className="note">Nothing to work on yet: no skill where {name} lags on the checked papers.</p>
      ) : (
        <>
          <ol className="grid gap-4" aria-label="Areas the next paper works on">
            {p.areas.map((a) => (
              <li key={a.skill_set} className="text-[13.5px]">
                <Link href={`/skill-sets/${a.skill_set}`} className="text-basalt no-underline hover:underline">{a.name}</Link>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <Pill tone="monsoon">{a.level}</Pill>
                  <span className="text-[12px] text-basalt/62">{a.questions.length} questions</span>
                </div>
                <div className="mt-1 text-[12.5px] text-terracotta">{a.why}</div>
                <ul className="mt-2 grid gap-1 text-[12.5px] text-basalt/80">
                  {a.questions.map((q) => (
                    <li key={q.item_key}>
                      <Link href={`/library/${q.item_key}`} className="text-basalt/80 no-underline hover:underline">{q.text}</Link>
                      {q.shows_mistake ? <span className="ml-1 text-terracotta">· can show the mistake</span> : null}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          <form action={approveNextPaper} className="mt-4">
            <input type="hidden" name="child_id" value={childId} />
            <input type="hidden" name="week" value={week} />
            <button className="btn" type="submit">Approve this paper</button>
            <p className="note mt-2">Approving prints it in your name as {name}&rsquo;s paper for this week.</p>
          </form>
        </>
      )}
      <p className="note mt-4">
        Chosen from the ladder: skills with a repeating mistake, under half right, or not yet four in five — weakest
        first, at most three. Questions come at random from the bank at that level, none {name} has been given, the ones
        that can show the repeating mistake first.
      </p>
    </Panel>
    </section>
  );
}
