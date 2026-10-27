// The child's home assessment, chosen from their own ladder (goals/s11-focus-paper.yaml, u2-children.yaml). The engine
// proposes (`w2_print/focus_paper.py`): this reads its plan and shows it in plain words — which areas, at what
// level, why — and every question it prints, before anything prints (goals/preview-before-print.yaml: Nimish,
// 2026-10-21, "a teacher can only see the assessment when they print"). "Different questions" draws others for the
// same skill and level and makes nothing. A teacher approves it with one button, which prints the questions shown. Made again the same week (Nimish, 2026-10-21: "There should not be
// any lock"), the newest is the week's: shown with who approved it, the earlier ones named as replaced in one line, and
// a new one is offered.
import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import { sql } from "@/lib/db";
import { EngineDown, engineGet } from "@/lib/engine";
import { isoWeek } from "@/lib/week";
import { seeHref } from "@/lib/next-paper";
import { DifferentQuestions, Questions } from "@/components/questions";
import { approveNextPaper } from "../actions";
import { fmtDate } from "./answers";

type Question = { item_key: string; text: string; fmt: string; shows_mistake: boolean };
type Area = { skill_set: string; name: string; level: string; right: number; answered: number; why: string; questions: Question[] };
type Approved = { qr: string; approved_by: string | null; approved_at: string | null; replaced: string[] };
type Plan = { week: string; areas: Area[]; n: number; seen: string; approved: Approved | null };

async function plan(childId: string, week: string, draw: number): Promise<Plan | string> {
  try {
    const res = await engineGet(`/child/${childId}/focus?week=${week}&draw=${draw}`);
    return res.ok ? ((await res.json()) as Plan) : `The engine could not make the plan (${res.status}).`;
  } catch (e) {
    return e instanceof EngineDown ? e.message : "The engine could not make the plan.";
  }
}

const TITLE = "Home assessment";

/** How long a question a child was given is held back from them: the `exposure.days` row the engine draws by. */
async function windowDays(): Promise<number> {
  const [r] = await sql<{ days: number }[]>`select coalesce((select value from threshold where key = 'exposure.days'), 21)::int as days`;
  return r.days;
}

export async function FocusPanel({ childId, name, staff, draw }: { childId: string; name: string; staff: Record<string, string>; draw: number }) {
  const week = isoWeek();
  const [p, days] = await Promise.all([plan(childId, week, draw), windowDays()]);
  return (
    <Panel title={TITLE} label={TITLE} aside={typeof p === "string" ? undefined : `${p.n} questions`}>
      {typeof p === "string" ? null : p.approved ? (
        <div className="mb-4 text-[13.5px]">
          <p>
            {p.approved.approved_by
              ? `Approved by ${staff[p.approved.approved_by] ?? p.approved.approved_by}${p.approved.approved_at ? ` on ${fmtDate(p.approved.approved_at)}` : ""}`
              : "Changed and waiting for approval"}
            : this week&rsquo;s home assessment, <Link href={`/papers/review/${p.approved.qr}`}>{p.approved.qr}</Link>. Review,
            change and print it from its page, or make a new one below.
          </p>
          {p.approved.replaced.length ? (
            <p className="note mt-1" data-replaced="">
              Replaced this week:{" "}
              {p.approved.replaced.map((qr, i) => (
                <span key={qr}>
                  {i ? ", " : ""}
                  <Link href={`/worksheets/${qr}`}>{qr}</Link>
                </span>
              ))}
              . A copy of one that comes back is still read and marked as that paper.
            </p>
          ) : null}
        </div>
      ) : null}
      {typeof p === "string" ? (
        <p className="note">{p}</p>
      ) : p.areas.length === 0 ? (
        <p className="note">Nothing to work on yet: no skill where {name} lags on the checked papers.</p>
      ) : (
        <>
          {p.approved ? <p className="mb-2 text-[13.5px] font-semibold">A new one would work on</p> : null}
          <ol className="grid gap-4" aria-label="Areas the home assessment works on">
            {p.areas.map((a) => (
              <li key={a.skill_set} className="text-[13.5px]">
                <Link href={`/skill-sets/${a.skill_set}`} className="text-basalt no-underline hover:underline">{a.name}</Link>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <Pill tone="monsoon">{a.level}</Pill>
                  <span className="text-[12px] text-basalt/62">
                    {a.questions.length} questions
                    {a.questions.some((q) => q.shows_mistake)
                      ? ` · ${a.questions.filter((q) => q.shows_mistake).length} can show the mistake`
                      : ""}
                  </span>
                </div>
                <div className="mt-1 text-[12.5px] text-terracotta">{a.why}</div>
                <Questions name={a.name} level={a.level} questions={a.questions} />
              </li>
            ))}
          </ol>
          <form action={approveNextPaper} className="mt-4">
            <input type="hidden" name="child_id" value={childId} />
            <input type="hidden" name="week" value={week} />
            {/* the paper this click replaces: a colleague's newer one made meanwhile turns it away, never two at once */}
            <input type="hidden" name="replaces" value={p.approved?.qr ?? ""} />
            {/* the questions shown are the questions printed (goals/preview-before-print.yaml) */}
            <input type="hidden" name="draw" value={draw} />
            <input type="hidden" name="seen" value={p.seen} />
            <div className="flex flex-wrap items-center gap-2">
              <button className="btn" type="submit">
                {p.approved ? "Make a new home assessment" : "Approve this home assessment"}
              </button>
              <DifferentQuestions href={`/growth/${childId}?draw=${draw + 1}`} />
              <a href={seeHref(childId, week, [], draw)} target="_blank" rel="noreferrer" className="ml-1 text-[13px]">
                See it as it will print
              </a>
            </div>
            <p className="note mt-2">
              {p.approved
                ? `Making it prints it in your name as ${name}\u2019s home assessment for this week, in place of ${p.approved.qr}, with questions ${name} has not been given. `
                : `Approving prints it in your name as ${name}\u2019s home assessment for this week. `}
              <Link href={`/make/custom?child=${childId}`}>Choose a different home assessment</Link>
            </p>
          </form>
        </>
      )}
      <p className="note mt-4">
        Chosen from the ladder: skills with a repeating mistake, under half right, or not yet four in five — weakest
        first, at most three. Questions come at random from the bank at that level, none {name} has been given in the last {days} days, the ones
        that can show the repeating mistake first.
      </p>
    </Panel>
  );
}
