import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { Panel } from "@/components/shell";
import { Score, StandingChip } from "@/components/standing";
import type { Evidence } from "@/lib/queries";
import { PURPOSE, type ChildSkill, type Repeated } from "@/lib/queries-children";
import type { TopicPaper } from "@/lib/queries-results";
import { byTopic, NEED, topicNote, topicStanding, type TopicStanding } from "@/lib/profile";
import type { Rag } from "@/lib/rag";
import type { States } from "@/lib/states";
import type { Column } from "@/lib/ux-rules";
import { dateWords } from "@/lib/week";
import { SkillLine } from "./skills-panel";

// A child's page, a row per topic (goals/res_results_by_topic.yaml). Nimish, 24 Oct 2026: "Child page: a row per topic with
// level, score, strength or weakness", and "Validation is embedded: the child's two or three page images are openable per
// assessment." Each row: the level of the newest question they answered in it, their last paper's score in it (the three
// signals apart), their state, one line of strength or weakness worked out by code. A topic opens to its skills (each to
// the answers behind it) and its papers, each paper to the pages the child wrote, here on the page.

type Row = { code: string; name: string; counts: TopicStanding; skills: ChildSkill[]; level: string | null; last: TopicPaper | null; note: string | null };
type Level = { code: string; topic_code: string; level: string; at: string; ord: number };

export function TopicsPanel({
  id,
  name,
  open,
  skills,
  answers,
  names,
  mistakes,
  papers,
  levels,
  states,
}: {
  id: string;
  name: string;
  open?: string;
  skills: ChildSkill[];
  answers: Evidence[];
  names: Record<string, string>;
  mistakes: Repeated[];
  papers: TopicPaper[];
  levels: Level[];
  states: States;
}) {
  const repeating = (s: ChildSkill) => mistakes.find((m) => m.rung_code === s.rung_code && m.skill_code === s.skill_code)?.name ?? null;
  const rows: Row[] = byTopic(skills, states).map((t) => {
    const mine = skills.filter((s) => s.topic_code === t.code);
    const newest = levels.filter((l) => l.topic_code === t.code).sort((a, b) => b.at.localeCompare(a.at) || b.ord - a.ord)[0];
    return { code: t.code, name: t.name, counts: t, skills: mine, level: newest?.level ?? null, last: papers.find((p) => p.topic_code === t.code) ?? null, note: topicNote(mine, states, repeating) };
  });
  // the topic asked for is open; with none asked for, every topic with a skill that needs help (goals/ux4-class-and-child.yaml)
  const isOpen = (r: Row) => (open ? r.code === open : topicStanding(r.skills, states) === "red");
  const href = (r: Row) => (isOpen(r) ? `/growth/${id}?topic=none#topics` : `/growth/${id}?topic=${r.code}#topic-${r.code}`);
  const columns: Column<Row>[] = [
    {
      key: "topic",
      label: "Topic",
      width: "14rem",
      value: (r) => r.name,
      cell: (r) => (
        <Link id={`topic-${r.code}`} href={href(r)} aria-expanded={isOpen(r)} className="scroll-mt-24 font-medium no-underline hover:underline">
          <span aria-hidden="true" className="mr-1.5 inline-block w-3 text-basalt/55">
            {isOpen(r) ? "▾" : "▸"}
          </span>
          {r.name}
        </Link>
      ),
    },
    // the topic's skills counted by where they stand, and those no paper has reached: what the row's state is read from
    { key: "skills", label: "Skills", width: "12rem", value: (r) => skillCounts(r.counts, states) },
    { key: "level", label: "Level", width: "6rem", value: (r) => r.level },
    {
      key: "last",
      label: "Last assessment",
      width: "13rem",
      value: (r) => (r.last ? r.last.date : null),
      cell: (r) =>
        r.last ? (
          <span>
            <Score s={r.last} />
            <span className="block text-[11.5px] text-basalt/55">{dateWords(r.last.date)}</span>
          </span>
        ) : null,
    },
    { key: "state", label: "State", status: true, width: "10rem", keep: true, value: (r) => topicStanding(r.skills, states), cell: (r) => <StandingChip standing={topicStanding(r.skills, states)} states={states} /> },
    { key: "note", label: "Strength or weakness", value: (r) => r.note, cell: (r) => (r.note ? <span className="text-[13px]">{r.note}</span> : null) },
  ];
  return (
    <Panel id="topics" label="What their answers show" title="What their answers show" aside="topic by topic, from checked answers only">
      <DataTable
        label="Topics"
        columns={columns}
        rows={rows}
        rowKey={(r) => r.code}
        more={{ page: 1, href: () => `/growth/${id}` }}
        limit={rows.length}
        extras={{
          attrs: (r) => ({ "data-topic": r.code }),
          expand: (r) =>
            isOpen(r) ? (
              <TopicOpen name={name} row={r} answers={answers} names={names} states={states} papers={papers.filter((p) => p.topic_code === r.code)} />
            ) : null,
        }}
      />
    </Panel>
  );
}

const COUNTED: Rag[] = ["red", "amber", "green", "grey"];
/** A topic's skills by colour, in each colour's count words, then those not assessed yet: only the counts that are not nought. */
function skillCounts(t: TopicStanding, states: States): string {
  return [...COUNTED.map((c) => [t[c], states.colours[c].count_words] as const), [t.notYet, "not assessed yet"] as const]
    .filter(([n]) => n)
    .map(([n, words]) => `${n} ${words}`)
    .join(" · ");
}

function TopicOpen({ name, row, answers, names, states, papers }: { name: string; row: Row; answers: Evidence[]; names: Record<string, string>; states: States; papers: TopicPaper[] }) {
  const rag = (s: ChildSkill) => states.of(s.state).colour;
  const assessed = row.skills.filter((s) => s.n_events > 0).sort((a, b) => NEED[rag(a)] - NEED[rag(b)]);
  const notYet = row.skills.filter((s) => s.n_events === 0);
  return (
    <div className="grid gap-4 py-2 pl-5 md:grid-cols-2">
      <section aria-label={`${row.name}: skills`}>
        <h3 className="label mb-2">Skills</h3>
        {assessed.length ? (
          <ul aria-label={row.name} className="grid gap-2">
            {assessed.map((s) => (
              <SkillLine
                key={`${s.code}|${s.skill_code}`}
                s={s}
                of={assessed.filter((x) => x.code === s.code).length > 1 ? s.skill_name : null}
                answers={answers.filter((a) => a.rung_code === s.rung_code && (!s.skill_code || a.skill_code === s.skill_code))}
                names={names}
                states={states}
              />
            ))}
          </ul>
        ) : null}
        {notYet.length ? <p className="note mt-2">Not assessed yet: {notYet.map((s) => s.name).join(" · ")}</p> : null}
      </section>
      <section aria-label={`${row.name}: papers`}>
        <h3 className="label mb-2">Papers</h3>
        {papers.length ? (
          <ul className="grid gap-2">
            {papers.map((p) => (
              <li key={p.capture_id} data-paper={p.qr_code} className="border border-basalt/12 px-3 py-2 text-[13.5px]">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="fact text-[12.5px] text-basalt/65">{dateWords(p.date)}</span>
                  <span className="font-medium">{p.title}</span>
                  <span className="text-[12.5px] text-basalt/65">{(p.kind && PURPOSE[p.kind]) || "earlier paper"}</span>
                  <span className="ml-auto">
                    <Score s={p} />
                  </span>
                </div>
                {/* the pages the child wrote, opened here: the photograph is the check on every number above it */}
                <details className="mt-2">
                  <summary className="cursor-pointer text-[13px] text-basalt/80 underline underline-offset-2">See the child’s page</summary>
                  <div className="mt-2 grid gap-2">
                    {p.pages.map((n) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img key={n} src={`/api/scan/${p.capture_id}/${n}`} alt={`${name}'s written page ${n}, paper ${p.qr_code}`} loading="lazy" className="w-full border border-basalt/14 bg-chalk" />
                    ))}
                    <Link href={`/worksheets/${p.qr_code}`} className="text-[12.5px]">
                      Open the whole paper →
                    </Link>
                  </div>
                </details>
              </li>
            ))}
          </ul>
        ) : (
          <p className="note">No checked paper in this topic yet.</p>
        )}
      </section>
    </div>
  );
}
