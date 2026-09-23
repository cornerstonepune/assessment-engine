import { Panel, Pill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";
import { STATE_WORDS } from "@/lib/queries";
import type { ChildSkill } from "@/lib/queries-children";
import { rag } from "@/lib/rag";
import { AnswerTable, fmtDate } from "./answers";

// What a child's checked answers show (goals/v2-what-answers-show.yaml): one line per skill their answers reach,
// topic by topic — its score, what it means, the mistake that repeats — opening to the answers behind it. Skills no
// paper has reached are named once, in a line, not drawn as a wall of grey.
export function SkillsPanel({ skills, answers, names }: { skills: ChildSkill[]; answers: Evidence[]; names: Record<string, string> }) {
  const assessed = skills.filter((s) => s.n_events > 0);
  const notYet = skills.filter((s) => s.n_events === 0);
  const topics = [...new Set(assessed.map((s) => s.topic))];
  return (
    <Panel id="skills" label="What their answers show" title="What their answers show" aside="from checked answers only">
      {assessed.length ? (
        topics.map((t) => (
          <div key={t} className="mb-4 last:mb-0">
            <h3 className="mb-2 font-heading text-[15px]">{t}</h3>
            <ul aria-label={t} className="grid gap-2">
              {assessed
                .filter((s) => s.topic === t)
                .map((s) => (
                  <SkillLine key={s.code} s={s} answers={answers.filter((a) => a.rung_code === s.rung_code)} names={names} />
                ))}
            </ul>
          </div>
        ))
      ) : (
        <p className="note">No checked answers yet. This fills in once a paper is read and checked.</p>
      )}
      {notYet.length ? (
        <p className="note mt-4" data-testid="not-yet">
          Not assessed yet: {notYet.map((s) => s.name).join(" · ")}
        </p>
      ) : null}
    </Panel>
  );
}

function SkillLine({ s, answers, names }: { s: ChildSkill; answers: Evidence[]; names: Record<string, string> }) {
  const state = s.state ?? "not_enough_yet";
  const words = STATE_WORDS[state];
  const blank = answers.filter((a) => a.status === "blank").length;
  return (
    <li data-rag={rag(s.state)} data-skill={s.code}>
      <details className="rounded-md border border-basalt/12">
        <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-[13.5px]">
          <span className="min-w-[150px] font-medium text-basalt">{s.name}</span>
          <span className="fact">
            {s.n_correct} of {s.n_events} right
          </span>
          <Pill tone={words.tone}>{state === "not_enough_yet" ? "too few answers to say" : words.words}</Pill>
          {s.repeating_misconception ? (
            <span className="text-[12.5px] text-terracotta">
              keeps: {names[s.repeating_misconception] ?? s.repeating_misconception}
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
