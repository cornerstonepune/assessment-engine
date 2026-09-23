// The child's next paper, chosen from their own ladder (goals/s11-focus-paper.yaml). The choosing is the
// engine's (`w2_print/focus_paper.py`): this reads its plan and shows it in plain words — which areas,
// why, the questions — with one button that prints it.
import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import { EngineDown, engineGet } from "@/lib/engine";
import { makeFocusPaper } from "../actions";

type Question = { item_key: string; text: string; fmt: string; shows_mistake: boolean };
type Area = { skill_set: string; name: string; level: string; right: number; answered: number; why: string; questions: Question[] };
type Plan = { week: string; areas: Area[]; n: number };

/** The ISO week, "2026-W39": a paper chosen in one week is the same paper however often the page opens. */
export function isoWeek(d = new Date()): string {
  const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  const first = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const n = Math.ceil(((t.getTime() - first.getTime()) / 86_400_000 + 1) / 7);
  return `${t.getUTCFullYear()}-W${String(n).padStart(2, "0")}`;
}

async function plan(childId: string, week: string): Promise<Plan | string> {
  try {
    const res = await engineGet(`/child/${childId}/focus?week=${week}`);
    return res.ok ? ((await res.json()) as Plan) : `The engine could not make the plan (${res.status}).`;
  } catch (e) {
    return e instanceof EngineDown ? e.message : "The engine could not make the plan.";
  }
}

export async function FocusPanel({ childId, name, made }: { childId: string; name: string; made?: string }) {
  const week = isoWeek();
  const p = await plan(childId, week);
  return (
    <Panel title="Next paper, from their own work" aside={typeof p === "string" ? undefined : `${p.n} questions`}>
      {made ? (
        <p className="mb-3 text-[13.5px]">
          Paper made: <Link href={`/worksheets/${made}`}>{made}</Link>. Print it from its page.
        </p>
      ) : null}
      {typeof p === "string" ? (
        <p className="note">{p}</p>
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
          <form action={makeFocusPaper} className="mt-4">
            <input type="hidden" name="child_id" value={childId} />
            <input type="hidden" name="week" value={week} />
            <button className="btn" type="submit">Make this paper</button>
          </form>
        </>
      )}
      <p className="note mt-4">
        Chosen from the ladder: skills with a repeating mistake, under half right, or not yet four in five — weakest
        first, at most three. Questions come at random from the bank at that level, none {name} has been given, the ones
        that can show the repeating mistake first.
      </p>
    </Panel>
  );
}
