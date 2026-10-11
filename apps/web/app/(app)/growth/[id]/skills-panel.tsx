import { mistakeName } from "@/lib/mistake-name";
import { Panel, Pill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";
import { STATE_WORDS } from "@/lib/queries";
import type { ChildSkill } from "@/lib/queries-children";
import { rag } from "@/lib/rag";
import { NEED } from "@/lib/profile";
import { AnswerTable, fmtDate } from "./answers";

// What a child's checked answers show (goals/v2-what-answers-show.yaml), topic by topic (goals/ui4b1-child-by-topic.yaml):
// each topic they are taught, its skills one line each, those that need help first — its score, what it means, the
// mistake that repeats — opening to the answers behind it. A topic's skills no paper has reached are named once, in a
// line under it, not drawn as a wall of grey.
export function SkillsPanel({ skills, answers, names }: { skills: ChildSkill[]; answers: Evidence[]; names: Record<string, string> }) {
  const topics = [...new Map(skills.map((s) => [s.topic_code, s.topic])).entries()];
  const assessed = skills.filter((s) => s.n_events > 0);
  return (
    <Panel id="skills" label="What their answers show" title="What their answers show" aside="from checked answers only">
      {assessed.length ? null : <p className="note mb-4">No checked answers yet. This fills in once a paper is read and checked.</p>}
      {topics.map(([code, name]) => {
        const here = assessed.filter((s) => s.topic_code === code).sort((a, b) => NEED[rag(a.state)] - NEED[rag(b.state)]);
        const notYet = skills.filter((s) => s.topic_code === code && s.n_events === 0);
        return (
          <section key={code} id={`topic-${code}`} className="mb-5 scroll-mt-6 last:mb-0">
            <h3 className="mb-2 font-heading text-[15px]">{name}</h3>
            {here.length ? (
              <ul aria-label={name} className="grid gap-2">
                {here.map((s) => (
                  <SkillLine
                    key={`${s.code}|${s.skill_code}`}
                    s={s}
                    // a rung that tests two skills is a line for each, the same name twice unless each says its skill
                    of={assessed.filter((x) => x.code === s.code).length > 1 ? s.skill_name : null}
                    answers={answers.filter((a) => a.rung_code === s.rung_code)}
                    names={names}
                  />
                ))}
              </ul>
            ) : null}
            {notYet.length ? (
              <p className="note mt-2" data-testid="not-yet">
                Not assessed yet: {notYet.map((s) => s.name).join(" · ")}
              </p>
            ) : null}
          </section>
        );
      })}
    </Panel>
  );
}

function SkillLine({ s, of, answers, names }: { s: ChildSkill; of: string | null; answers: Evidence[]; names: Record<string, string> }) {
  const state = s.state ?? "not_enough_yet";
  const words = STATE_WORDS[state];
  const blank = answers.filter((a) => a.status === "blank").length;
  return (
    <li data-rag={rag(s.state)} data-skill={s.code} data-of={s.skill_code ?? undefined}>
      <details className="rounded-md border border-basalt/12">
        <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-[13.5px]">
          <span className="min-w-[150px] font-medium text-basalt">
            {s.name}
            {of ? <span className="font-normal text-basalt/62"> · {of}</span> : null}
          </span>
          <span className="fact">
            {s.n_correct} of {s.n_events} right
          </span>
          <Pill tone={words.tone}>{state === "not_enough_yet" ? "too few answers to say" : words.words}</Pill>
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
