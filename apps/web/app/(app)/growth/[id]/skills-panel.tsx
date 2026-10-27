import { mistakeName } from "@/lib/mistake-name";
import { Pill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";
import type { ChildSkill } from "@/lib/queries-children";
import { RAG_TONE } from "@/lib/rag";
import type { States } from "@/lib/states";
import { AnswerTable, fmtDate } from "./answers";

// One skill of a child's, a line that opens to the answers behind it (goals/v2-what-answers-show.yaml): its score, what it
// means, the mistake that repeats on it. The topic it belongs to is a row of the child's page (./topics-panel.tsx).
export function SkillLine({ s, of, answers, names, states }: { s: ChildSkill; of: string | null; answers: Evidence[]; names: Record<string, string>; states: States }) {
  const state = states.of(s.state);
  const blank = answers.filter((a) => a.status === "blank").length;
  return (
    <li data-rag={state.colour} data-skill={s.code} data-of={s.skill_code ?? undefined}>
      <details className="rounded-md border border-basalt/12">
        <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-[13.5px]">
          <span className="min-w-[150px] font-medium text-basalt">
            {s.name}
            {of ? <span className="font-normal text-basalt/62"> · {of}</span> : null}
          </span>
          <span className="fact">
            {s.n_correct} of {s.n_events} right
          </span>
          <Pill tone={RAG_TONE[state.colour]}>{states.say(s.state)}</Pill>
          {s.repeating_misconception ? (
            <span className="text-[12.5px] text-terracotta">
              keeps: {mistakeName(names, s.repeating_misconception, null, s.skill_code)}
            </span>
          ) : null}
          {blank ? <span className="text-[12px] text-basalt/62">{blank} left blank</span> : null}
          <span className="ml-auto text-[12px] text-basalt/55">last seen {fmtDate(s.last_seen)}</span>
        </summary>
        <div className="border-t border-basalt/12">
          {answers.length ? <AnswerTable rows={answers} names={names} /> : <p className="note p-3">The answers are on papers not yet re-read.</p>}
        </div>
      </details>
    </li>
  );
}
