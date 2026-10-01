import Link from "@/components/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Body, PageHeader } from "@/components/shell";
import { ColourKey, Swatch } from "@/components/colour-key";
import { requireStaff } from "@/lib/auth";
import { checkHref, checkLevel, colourRules } from "@/lib/colours";
import { classGrid, stepKey, type GridChild, type Step } from "@/lib/queries-children";
import { STATE_WORDS } from "@/lib/queries";
import { rag } from "@/lib/rag";
import { deadline } from "@/lib/deadline";
import { ChecksPanel, type Check } from "../../checks";

type Props = { params: Promise<{ section: string }> };

// A class: its children down the side, across the top every skill someone in the class has been assessed on, topic by
// topic; each cell the child's score in the colour of the graph's own state (goals/v2-what-answers-show.yaml). A skill
// no one has answered yet is named once below, not drawn as a column of grey. The colour is lib/rag.ts's.
export default async function ClassPage({ params }: Props) {
  const me = await requireStaff();
  const section = decodeURIComponent((await params).section);
  const [{ steps, children, notYet, band }, rules] = await deadline(Promise.all([classGrid(section, me.email), colourRules()]));
  if (!children.length) notFound();
  // the check that would place each child too few answers say anything about: one a skill, for every child grey on
  // any of its columns (a rung that tests two skills is two columns, and was two checks of the one skill), then every
  // skill of the grade no child has answered, for the whole class — it had no check at all (code review, 2026-09-30)
  const check = (skill: { code: string; name: string; levels: string[] }, kids: GridChild[], who: ReactNode): Check => {
    const level = checkLevel(rules, band, skill.levels);
    const href = checkHref(section, kids.map((k) => k.id), skill.code, level, rules.checkSize);
    return { key: skill.code, skill: skill.name, who, level, n: rules.checkSize, href };
  };
  const answered = [...new Map(steps.map((s) => [s.skill_set, { code: s.skill_set, name: s.descriptor, levels: s.levels }])).values()];
  const checks: Check[] = [
    ...answered.flatMap((skill) => {
      const columns = steps.filter((s) => s.skill_set === skill.code);
      const grey = (c: GridChild) => columns.some((s) => (c.states[stepKey(s)]?.state ?? "not_enough_yet") === "not_enough_yet");
      const answers = (c: GridChild) => Math.max(...columns.map((s) => c.states[stepKey(s)]?.n_events ?? 0));
      const kids = children.filter(grey);
      return kids.length ? [check(skill, kids, <Who kids={kids} answers={answers} />)] : [];
    }),
    ...notYet.map((u) => check(u, children, `All ${children.length}: none has answered it yet`)),
  ];
  const topics = [...new Set(steps.map((s) => s.topic_name))];
  const firstOfTopic = (i: number) => i === 0 || steps[i - 1].topic_name !== steps[i].topic_name;

  return (
    <>
      <PageHeader
        stage="Children · class"
        title={section}
        sub={`${children.length} ${children.length === 1 ? "child" : "children"} against every skill the class has been assessed on, topic by topic — each child's score from checked papers only. A name opens the child.`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12.5px] text-basalt/62">
          <Link href="/growth" className="chip">
            ← All classes
          </Link>
        </p>
        {steps.length ? null : <p className="note mb-3">No checked answers in this class yet.</p>}
        <div className="panel overflow-x-auto">
          <table className="grid" aria-label={`${section}: each child on each step`}>
            <thead>
              <tr>
                <th rowSpan={2} className="pin">
                  Child
                </th>
                {topics.map((t) => (
                  <th key={t} colSpan={steps.filter((s) => s.topic_name === t).length} className="num border-l border-basalt/12">
                    {t}
                  </th>
                ))}
              </tr>
              <tr>
                {steps.map((s, i) => (
                  <th
                    key={stepKey(s)}
                    data-col={stepKey(s)}
                    title={s.descriptor}
                    className={`num min-w-[96px] max-w-[120px] align-top ${firstOfTopic(i) ? "border-l border-basalt/12" : ""}`}
                  >
                    {/* the table's headings are small capitals; a step's words are a sentence, so they are set as one */}
                    <span className="line-clamp-3 block text-[11.5px] font-normal normal-case leading-tight tracking-normal text-basalt/75">
                      {s.descriptor}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {children.map((c) => (
                <tr key={c.id} data-child={c.id}>
                  {/* the names stay put while a phone scrolls the steps */}
                  <td className="pin whitespace-nowrap">
                    <span className="fact mr-2 text-basalt/55">{c.roll_no}</span>
                    <Link href={`/growth/${c.id}`} className="underline decoration-basalt/30 underline-offset-4">
                      {c.first_name}
                    </Link>
                  </td>
                  {steps.map((s, i) => (
                    <Cell key={stepKey(s)} step={s} first={firstOfTopic(i)} got={c.states[stepKey(s)]} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {notYet.length ? (
          <p className="note mt-3" data-testid="not-yet">
            Not assessed yet in this class: {notYet.map((u) => u.name).join(" · ")}
          </p>
        ) : null}
        <p className="note mt-3">
          Columns follow the Curriculum: topic by topic, each skill easy to hard. A cell is the child&rsquo;s right answers of all they
          answered; its colour is said below.
        </p>
        <div className="mt-[18px] grid gap-[18px]">
          <ColourKey rules={rules} />
          <ChecksPanel title="Checks that would place them" whoHeading="Children without enough answers" checks={checks} />
        </div>
      </Body>
    </>
  );
}

function Cell({ step, first, got }: { step: Step; first: boolean; got?: { state: string; n_events: number; n_correct: number } }) {
  const colour = rag(got?.state);
  const said = `${step.skill_name} — ${got?.n_events ? `${got.n_correct} of ${got.n_events} right, ${STATE_WORDS[got.state].words}` : "no answers yet"}`;
  return (
    <td data-col={stepKey(step)} data-rag={colour} title={said} className={`num ${first ? "border-l border-basalt/12" : ""}`}>
      {got?.n_events ? (
        <span className="inline-flex items-center gap-1">
          <Swatch colour={colour} label={said} />
          <span className="fact text-[12px]">
            {got.n_correct}/{got.n_events}
          </span>
        </span>
      ) : (
        <span className="text-basalt/30" aria-label={said}>
          —
        </span>
      )}
    </td>
  );
}

/** Who a check is for: each child, and how many answers they have on the skill so far. */
function Who({ kids, answers }: { kids: GridChild[]; answers: (k: GridChild) => number }) {
  return (
    <>
      {kids.map((k, i) => {
        const n = answers(k);
        return (
          <span key={k.id} className="whitespace-nowrap">
            {k.first_name} <span className="text-basalt/55">({n ? `${n} answer${n === 1 ? "" : "s"}` : "none"})</span>
            {i < kids.length - 1 ? ", " : ""}
          </span>
        );
      })}
    </>
  );
}
