import { mistakeName } from "@/lib/mistake-name";
import { Panel, Pill } from "@/components/shell";
import type { Evidence } from "@/lib/queries";
import { STATE_WORDS } from "@/lib/queries";
import type { ChildSkill } from "@/lib/queries-children";
import { rag, type Rag } from "@/lib/rag";
import { byTopic, NEED, type TopicStanding } from "@/lib/profile";
import { AnswerTable, fmtDate } from "./answers";

// What a child's checked answers show (goals/v2-what-answers-show.yaml), topic by topic (goals/ui4b1-child-by-topic.yaml),
// and the only place their page says it beyond its one sentence (goals/ux4-class-and-child.yaml): each topic they are
// taught a group whose line counts its skills by where they stand, open where a skill needs help; inside, its skills one
// line each, those that need help first — its score, what it means, the mistake that repeats — opening to the answers
// behind it. A topic's skills no paper has reached are named once, in a line under it, not drawn as a wall of grey.
const COUNTS: [Rag | "notYet", string][] = [
  ["red", "needs help"],
  ["amber", "practising"],
  ["green", "secure"],
  ["grey", "too few answers"],
  ["notYet", "not assessed yet"],
];

export function SkillsPanel({ skills, answers, names }: { skills: ChildSkill[]; answers: Evidence[]; names: Record<string, string> }) {
  const assessed = skills.filter((s) => s.n_events > 0);
  return (
    <Panel id="skills" label="What their answers show" title="What their answers show" aside="from checked answers only">
      {assessed.length ? null : <p className="note mb-4">No checked answers yet. This fills in once a paper is read and checked.</p>}
      {byTopic(skills).map((t) => {
        const { code, name } = t;
        const here = assessed.filter((s) => s.topic_code === code).sort((a, b) => NEED[rag(a.state)] - NEED[rag(b.state)]);
        const notYet = skills.filter((s) => s.topic_code === code && s.n_events === 0);
        return (
          <details
            key={code}
            id={`topic-${code}`}
            data-topic={code}
            open={t.red > 0}
            className="group mb-3 scroll-mt-6 border-t border-basalt/10 pt-3 first:border-t-0 first:pt-0 last:mb-0"
          >
            <summary className="flex cursor-pointer list-none flex-wrap items-baseline gap-x-2 gap-y-1 pb-2 [&::-webkit-details-marker]:hidden">
              <span aria-hidden="true" className="inline-block w-3 text-basalt/50 transition-transform group-open:rotate-90">
                ▸
              </span>
              <h3 className="font-heading text-[15px]">{name}</h3>
              <Counts t={t} />
            </summary>
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
          </details>
        );
      })}
    </Panel>
  );
}

/** A topic's line: its skills counted by where they stand, only the counts that are not nought. */
function Counts({ t }: { t: TopicStanding }) {
  return (
    <span className="text-[12.5px] text-basalt/70">
      {COUNTS.filter(([k]) => t[k])
        .map(([k, words]) => `${t[k]} ${words}`)
        .join(" · ")}
    </span>
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
