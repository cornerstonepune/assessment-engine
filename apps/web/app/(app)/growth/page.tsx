import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { NotYours } from "@/components/not-yours";
import { EmptyState } from "@/components/empty-state";
import { ColourKeyLine } from "@/components/colour-key";
import { requireStaff } from "@/lib/auth";
import { reachOf, workScope } from "@/lib/reach";
import { isMine } from "@/lib/scope";
import { classesOf } from "@/lib/taught";
import { colourRules } from "@/lib/colours";
import { childStates } from "@/lib/states";
import { deadline } from "@/lib/deadline";
import { classTopics } from "@/lib/queries-results";
import { NOT_ASSESSED } from "@/components/standing";
import { ChildrenView } from "./children-view";
import { TopicsTable, type Open } from "./by-topic";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// What only the children-by-child view read: an address carrying one is a bookmark of it, and still opens it.
const CHILDREN_VIEW = ["sort", "status", "grade", "page", "cpage"];

// Class results (goals/res_results_by_topic.yaml). Nimish, 24 Oct 2026: "The unit of reference is the topic: Subject, then
// Topic, then Skill, then difficulty levels" and "Class view: topics as rows, children inside". One class at a time, chosen
// in the page's own filter row, opening on the educator's own; a class the person may not see is refused in words.
export default async function ClassResults({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  if (q.view === "children" || CHILDREN_VIEW.some((k) => q[k])) return <ChildrenView me={me} q={q} />;
  const [reach, own] = await deadline(Promise.all([reachOf(me), workScope(me)]));
  if (q.class && !isMine(reach, q.class)) return <NotYours what={`Class ${q.class}`} />;
  const [classes, mine] = await deadline(Promise.all([classesOf(reach), classesOf(own)]));
  const section = q.class ?? mine[0] ?? classes[0];
  const shell = (body: React.ReactNode) => (
    <PageShell
      stage="Class results"
      title="Class results"
      purpose="Each topic of the class: who is secure, practising or needs help. Open a topic for its skills, a skill for its children."
      action={
        <Link href="/papers/make?kind=assessment&way=same" className="btn">
          Make an assessment
        </Link>
      }
      next={{ href: "/today", label: "Today" }}
    >
      {body}
    </PageShell>
  );
  if (!section) return shell(<EmptyState>You are linked to no class yet. The coordinator links you to the classes you teach.</EmptyState>);

  const [topics, states, rules] = await deadline(Promise.all([classTopics(section, me), childStates(), colourRules()]));
  const subjects = [...new Map(topics.map((t) => [t.subject_code, t.subject])).entries()];
  const subject = subjects.some(([c]) => c === q.subject) ? q.subject : undefined;
  const shown = topics.filter((t) => !subject || t.subject_code === subject);
  const o: Open = {
    section,
    subject,
    topic: shown.some((t) => t.code === q.topic) ? q.topic : undefined,
    skill: q.skill,
    page: Math.max(1, Math.floor(Number(q.kp)) || 1),
  };
  const words = (["green", "amber", "red", "grey"] as const).map((c) => states.colours[c].count_words);
  return shell(
    <div className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
      <FilterBar
        action="/growth"
        filters={[
          { name: "class", label: "Class", value: section, all: "Choose a class", required: true, options: (classes.includes(section) ? classes : [section, ...classes]).map((c) => [c, c] as const) },
          ...(subjects.length > 1 ? [{ name: "subject", label: "Subject", value: subject, all: "Every subject", options: subjects }] : []),
        ]}
      />
      <section aria-label={`Topics of ${section}`}>
        <h2 className="label mb-2">
          {section} · {shown.length} {shown.length === 1 ? "topic" : "topics"}
        </h2>
        <TopicsTable me={me} o={o} states={states} topics={shown} />
      </section>
      <p className="flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
        <Link href={`/growth/class/${encodeURIComponent(section)}`}>Each child against each topic →</Link>
        <Link href={`/growth?view=children&class=${encodeURIComponent(section)}`}>Every child, one by one →</Link>
      </p>
      {/* how the counts are read, and the key to the colours: put away until asked for */}
      <details className="text-[12px] text-basalt/65">
        <summary className="cursor-pointer text-basalt/55 underline underline-offset-2">Details</summary>
        <div className="mt-3 grid gap-3">
          <p className="note">
            From checked answers only. Each child is counted once in a topic, by the skill of it they are weakest on:
            {" "}&ldquo;{words.join("”, “")}&rdquo;. A child with no checked answer in the topic is &ldquo;{NOT_ASSESSED}&rdquo;. A
            child&rsquo;s level is the level of the newest question they answered on the skill.
          </p>
          <ColourKeyLine rules={rules} states={states} />
        </div>
      </details>
    </div>,
  );
}
