import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Score, SpreadCell, StandingChip, NOT_ASSESSED } from "@/components/standing";
import type { Session } from "@/lib/auth";
import { skillChildren, topicPapers, topicSkills, type ChildOnSkill, type PaperKind, type SkillLine, type TopicLine } from "@/lib/queries-results";
import { TABLE_ROW_LIMIT, type Column } from "@/lib/ux-rules";
import type { States } from "@/lib/states";
import { dateWords } from "@/lib/week";

// A class's results by topic (goals/res_results_by_topic.yaml). Nimish, 24 Oct 2026: "Class view: topics as rows, children
// inside." Subject, then topic, then skill, then the children: each level folded until it is opened, and each opened by
// its own address (?topic=, ?skill=), so only what is open is read, one query a level, and a link to it can be sent.

export type Open = { section: string; subject?: string; topic?: string; skill?: string; page: number };

/** The address of the class view with some of what is open changed. */
export function hrefOf(o: Open, change: Partial<Open>): string {
  const n = { ...o, ...change };
  const q = new URLSearchParams({ class: n.section });
  if (n.subject) q.set("subject", n.subject);
  if (n.topic) q.set("topic", n.topic);
  if (n.topic && n.skill) q.set("skill", n.skill);
  if (n.topic && n.skill && n.page > 1) q.set("kp", String(n.page));
  return `/growth?${q}${n.skill ? `#skill-${n.skill}` : n.topic ? `#topic-${n.topic}` : ""}`;
}

/** A row's name as the link that opens it, or folds it again: it says which, to a screen reader as to the eye. */
function Opener({ name, open, href, id }: { name: string; open: boolean; href: string; id: string }) {
  return (
    <Link id={id} href={href} aria-expanded={open} className="scroll-mt-24 font-medium no-underline hover:underline">
      <span aria-hidden="true" className="mr-1.5 inline-block w-3 text-basalt/55">
        {open ? "▾" : "▸"}
      </span>
      {name}
    </Link>
  );
}

export async function TopicsTable({ me, o, states, topics }: { me: Session; o: Open; states: States; topics: TopicLine[] }) {
  if (!topics.length) return <EmptyState>No topic is taught in {o.section} yet. A topic shows here once it is marked taught.</EmptyState>;
  const columns: Column<TopicLine>[] = [
    {
      key: "topic",
      label: "Topic",
      width: "16rem",
      value: (t) => t.name,
      cell: (t) => <Opener id={`topic-${t.code}`} name={t.name} open={t.code === o.topic} href={hrefOf(o, { topic: t.code === o.topic ? undefined : t.code, skill: undefined, page: 1 })} />,
    },
    { key: "children", label: "Children", keep: true, value: (t) => t.children, cell: (t) => <SpreadCell spread={t.spread} states={states} /> },
    { key: "last", label: "Last assessed", width: "9rem", keep: true, value: (t) => (t.last ? dateWords(t.last) : "not yet") },
  ];
  return (
    <DataTable
      label={`${o.section}: topics`}
      columns={columns}
      rows={topics}
      rowKey={(t) => t.code}
      more={o.subject ? { page: 1, href: () => hrefOf(o, {}) } : { by: (t) => t.subject, href: (g: string) => hrefOf(o, { subject: topics.find((t) => t.subject === g)?.subject_code }) }}
      limit={o.subject ? topics.length : TABLE_ROW_LIMIT}
      extras={{
        attrs: (t) => ({ "data-topic": t.code }),
        expand: (t) => (t.code === o.topic ? <TopicOpen me={me} o={o} states={states} /> : null),
      }}
    />
  );
}

/** One topic opened: the papers its children answered, by kind, then its skills easy to hard. */
async function TopicOpen({ me, o, states }: { me: Session; o: Open; states: States }) {
  const [skills, papers] = await Promise.all([topicSkills(o.section, o.topic!), topicPapers(o.section, o.topic!, me)]);
  const columns: Column<SkillLine>[] = [
    {
      key: "skill",
      label: "Skill",
      width: "16rem",
      value: (s) => s.name,
      cell: (s) => <Opener id={`skill-${s.code}`} name={s.name} open={s.code === o.skill} href={hrefOf(o, { skill: s.code === o.skill ? undefined : s.code, page: 1 })} />,
    },
    { key: "children", label: "Children", keep: true, value: (s) => s.children, cell: (s) => <SpreadCell spread={s.spread} states={states} /> },
    { key: "levels", label: "Level they are at", width: "11rem", value: (s) => s.levels.map((l) => `${l.n} at ${l.level}`).join(" · ") || null },
    { key: "last", label: "Last assessed", width: "9rem", keep: true, value: (s) => (s.last ? dateWords(s.last) : "not yet") },
  ];
  // a skill no child has answered is named once, under the table, never a row of grey (goals/ux4-class-and-child.yaml)
  const answered = skills.filter((s) => s.children > s.spread.none);
  const none = skills.filter((s) => s.children <= s.spread.none);
  return (
    <div className="grid gap-3 py-2 pl-5">
      <p data-testid="topic-papers" className="text-[13px] text-basalt/80">
        {papers.length ? papersWords(papers) : "No checked paper in this topic yet."}
      </p>
      {none.length ? (
        <p data-testid="skills-not-yet" className="note order-last">
          Not assessed yet: {none.map((s) => s.name).join(" · ")}
        </p>
      ) : null}
      {answered.length ? (
        <DataTable
          label={`${o.section}: skills of the topic`}
          columns={columns}
          rows={answered}
          rowKey={(s) => s.code}
          more={{ page: 1, href: () => hrefOf(o, {}) }}
          limit={Math.max(1, answered.length)}
          extras={{
            attrs: (s) => ({ "data-skill": s.code }),
            expand: (s) => (s.code === o.skill ? <SkillOpen me={me} o={o} states={states} /> : null),
          }}
        />
      ) : null}
    </div>
  );
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The topic's papers in the order the week runs them (Nimish, 24 Oct 2026: "skills, then baseline assessment, then home
 *  assessments (some children get more), then practice"). Home papers of every kind are one line. */
export function papersWords(papers: PaperKind[]): string {
  const of = (kinds: (string | null)[]) => papers.filter((p) => kinds.includes(p.kind));
  const sum = (ps: PaperKind[], f: (p: PaperKind) => number) => ps.reduce((n, p) => n + f(p), 0);
  const home = of(["focus", "custom", "home"]);
  const lines = [
    ...of(["assessment"]).map((p) => `${plural(p.sets, "class assessment")}, for ${plural(p.children, "child", "children")}`),
    ...(home.length
      ? [`${plural(sum(home, (p) => p.papers), "home assessment")}, for ${plural(Math.max(...home.map((p) => p.children)), "child", "children")}${Math.max(...home.map((p) => p.most)) > 1 ? ` (up to ${Math.max(...home.map((p) => p.most))} each)` : ""}`]
      : []),
    ...of(["practice"]).map((p) => `${plural(p.sets, "class practice paper")}, for ${plural(p.children, "child", "children")}`),
    ...of([null]).map((p) => `${plural(p.papers, "earlier paper")}, for ${plural(p.children, "child", "children")}`),
  ];
  return `Papers in this topic: ${lines.join(" · ")}.`;
}

/** One skill opened: its children, those who need the educator first, a page at a time. */
async function SkillOpen({ me, o, states }: { me: Session; o: Open; states: States }) {
  const { rows, of } = await skillChildren(o.section, o.skill!, me, o.page, TABLE_ROW_LIMIT);
  const columns: Column<ChildOnSkill>[] = [
    { key: "roll", label: "Roll", num: true, width: "4rem", value: (c) => c.roll_no },
    { key: "name", label: "Child", width: "8rem", value: (c) => c.first_name, cell: (c) => <Link href={`/growth/${c.id}`}>{c.first_name}</Link> },
    { key: "level", label: "Level", width: "7.5rem", value: (c) => c.level },
    {
      key: "state",
      label: "State",
      status: true,
      width: "10rem",
      keep: true,
      value: (c) => c.state ?? NOT_ASSESSED,
      cell: (c) => <StandingChip standing={c.state ? states.of(c.state).colour : "none"} states={states} />,
    },
    { key: "score", label: "Answers", width: "13rem", value: (c) => c.right + c.wrong + c.wrong_working + c.blank || null, cell: (c) => <Score s={c} /> },
    {
      key: "waiting",
      label: "Waiting",
      value: (c) => c.waiting || null,
      cell: (c) =>
        c.waiting ? (
          <Link href={`/growth/${c.id}#needs-you`} className="text-terracotta">
            {plural(c.waiting, "answer")} waiting to be checked: results may change
          </Link>
        ) : null,
    },
    { key: "last", label: "Last assessed", width: "9rem", value: (c) => (c.last ? dateWords(c.last) : "not yet") },
  ];
  return (
    <div className="py-2 pl-5">
      <DataTable
        label={`${o.section}: children on the skill`}
        columns={columns}
        rows={rows}
        rowKey={(c) => c.id}
        more={{ page: o.page, of, href: (n: number) => hrefOf(o, { page: n }) }}
        extras={{ attrs: (c) => ({ "data-child": c.id }) }}
      />
    </div>
  );
}
