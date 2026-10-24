import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { Notice } from "@/components/shell";
import { StatusChip, type State } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { choices } from "@/lib/choices";
import { deadline } from "@/lib/deadline";
import { scopeOf } from "@/lib/scope";
import { teaching, type TeachingTopic } from "@/lib/queries-teaching";
import { count } from "@/lib/todo";
import type { TopicStatus } from "@/lib/topic-flow";
import type { Column } from "@/lib/ux-rules";
import { subjectNow, subjectsFor } from "@/lib/viewing";
import { switchTopic } from "../topic-actions";
import { FlowStrip } from "./flow-strip";

// Teaching (goals/nav_teacher_scope_and_todo.yaml; it was Taught this week, and keeps its address). Nimish, 24 Oct 2026: "the
// teacher finally teaches at the level of a topic. When they start with a new topic they go through the skills; they generate
// some assessments; then they give a first baseline assessment; then as a child progresses they give home assessments ...
// When the teacher marks a topic taught, or generates an assessment on it, the system understands it is taught." A tab for
// each subject the person teaches; a table of its topics; each topic's flow in each class. Skills are approved in Setup,
// never here: a skill still waiting is a muted word. Every action is in a row's action column.
const STATUS: Record<TopicStatus, State> = { taught: "taught", teachingNow: "teachingNow", nextUp: "nextUp", notTaught: "notTaught" };
const FOLD = 3;

export default async function Teaching({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const q = await searchParams;
  const me = await requireStaff();
  const scope = scopeOf(me);
  const [all, offered] = await deadline(Promise.all([teaching(scope), choices()]));
  const mine = subjectsFor(me, offered.subjects);
  // a topic named in the address (What needs doing opens one) is that topic alone, under its own subject
  const said = q.on ?? q.off;
  const named = all.find((t) => t.code === q.topic && mine.some((s) => s.code === t.subject));
  // what was just said (of a topic or one of its skills) is shown under its own subject
  const justSaid = all.find((t) => t.code === said || t.skills.some((k) => k.code === said));
  const subject = mine.find((s) => s.code === (named?.subject ?? justSaid?.subject ?? q.subject)) ?? subjectNow(me, offered.subjects, me.subject) ?? mine[0];
  const status = (Object.keys(STATUS) as TopicStatus[]).find((s) => s === q.status);
  const topics = all.filter((t) => t.subject === subject?.code && (!named || t === named) && (!status || t.status === status));
  // said of a topic, or of one skill of it (the Curriculum row's switch comes back here)
  const switched = all.find((t) => t.code === said)?.name ?? all.flatMap((t) => t.skills).find((k) => k.code === said)?.name;
  const columns: Column<TeachingTopic>[] = [
    { key: "topic", label: "Topic", width: "13rem", value: (t) => t.name, cell: (t) => <b>{t.name}</b> },
    { key: "status", label: "Status", status: true, width: "10rem", keep: true, value: (t) => t.status, cell: (t) => <StatusChip state={STATUS[t.status]} /> },
    { key: "skills", label: "Skills", width: "12rem", value: (t) => t.skills.length, cell: (t) => <Skills t={t} /> },
    { key: "flow", label: "Topic flow", value: (t) => t.flows.length, cell: (t) => <Flows t={t} /> },
    { key: "result", label: "Class result", status: true, width: "10rem", keep: true, value: (t) => t.result, cell: (t) => <StatusChip state={t.result} /> },
    { key: "action", label: "", width: "15rem", keep: true, value: (t) => t.code, cell: (t) => <Action t={t} /> },
  ];
  return (
    <PageShell
      stage="Teaching"
      title="Teaching"
      purpose="Your topics, one subject at a time: what is taught, how each class has moved through the topic, and how it stands."
      action={
        <Link href="/papers" className="btn">
          Open Assessments →
        </Link>
      }
      next={{ href: "/papers", label: "Assessments" }}
      details={{ href: "/", label: "The whole curriculum" }}
    >
      {switched ? (
        <Notice tone="neem">
          {switched} is {q.on ? "" : "not "}taught in {q.class} now, in your name. No other class changed.
        </Notice>
      ) : null}
      {mine.length > 1 ? (
        <nav aria-label="Subjects" className="mb-3 flex gap-2">
          {mine.map((s) => (
            <Link key={s.code} href={`/taught?subject=${s.code}`} aria-current={s.code === subject?.code ? "page" : undefined} className={`chip ${s.code === subject?.code ? "on" : ""}`}>
              {s.label}
            </Link>
          ))}
        </nav>
      ) : null}
      <FilterBar
        action="/taught"
        keep={{ subject: subject?.code }}
        filters={[{ name: "status", label: "Status", value: status, all: "Every status", options: (Object.keys(STATUS) as TopicStatus[]).map((s) => [s, s === "notTaught" ? "Not taught yet" : s === "nextUp" ? "Next" : s === "teachingNow" ? "Teaching now" : "Taught"] as const) }]}
      />
      {topics.length ? (
        <DataTable label={`${subject?.label ?? ""} topics`} columns={columns} rows={topics} rowKey={(t) => t.code} extras={{ attrs: (t) => ({ "data-topic": t.code, "data-status": t.status }) }} more={{ page: Math.max(1, Number(q.page) || 1), href: (n: number) => `/taught?subject=${subject?.code}&page=${n}` }} />
      ) : (
        <EmptyState next={{ href: "/papers", label: "Assessments" }}>No topics{status ? " in that status" : ""} for {subject?.label ?? "this subject"}.</EmptyState>
      )}
    </PageShell>
  );
}

/** The skill count; open, each skill with its levels. A skill waiting for approval is a muted word, never a button: skills are approved in Setup. */
function Skills({ t }: { t: TeachingTopic }) {
  return (
    <details>
      <summary className="cursor-pointer">{count(t.skills.length, "skill")}</summary>
      <ul className="mt-2 grid gap-1 text-[13px]">
        {t.skills.map((s) => (
          <li key={s.code} data-skill={s.code}>
            <Link href={`/skill-sets/${s.code}`}>{s.name}</Link> <span className="text-basalt/55">· {s.levels.join(", ") || "no levels"}</span>
            {s.approved ? null : <span className="ml-1 text-basalt/45">· waiting for approval</span>}
          </li>
        ))}
      </ul>
    </details>
  );
}

function Flows({ t }: { t: TeachingTopic }) {
  if (!t.flows.length) return <span className="text-basalt/45">No class yet</span>;
  const shown = t.flows.slice(0, FOLD);
  const rest = t.flows.slice(FOLD);
  return (
    <div className="grid gap-1">
      {shown.map((c) => (
        <FlowStrip key={c.section} cls={c} />
      ))}
      {rest.length ? (
        <details>
          <summary className="cursor-pointer text-[12.5px] text-basalt/65">{rest.length} more {rest.length === 1 ? "class" : "classes"}</summary>
          <div className="mt-1 grid gap-1">
            {rest.map((c) => (
              <FlowStrip key={c.section} cls={c} />
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}

/** The row's one action: say a class has been taught the topic, in the person's name, or, once every class has, not after all.
 *  A class taught can be said not taught from the fold under it; and the way to the topic's assessments. */
function Action({ t }: { t: TeachingTopic }) {
  const allTaught = t.untaught.length === 0 && t.taught.length > 0;
  return (
    <div className="grid gap-2">
      {t.untaught.length ? <Say t={t} classes={t.untaught} on /> : null}
      {allTaught ? <Say t={t} classes={t.taught} on={false} /> : null}
      {t.taught.length && t.untaught.length ? (
        <details>
          <summary className="cursor-pointer text-[13px] text-basalt/65">Not taught after all</summary>
          <div className="mt-2">
            <Say t={t} classes={t.taught} on={false} plain />
          </div>
        </details>
      ) : null}
      <Link href={`/papers?topic=${t.code}`} className="text-[13px]">
        Assessments on this topic →
      </Link>
    </div>
  );
}

function Say({ t, classes, on, plain }: { t: TeachingTopic; classes: string[]; on: boolean; plain?: boolean }) {
  return (
    <form action={switchTopic} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={t.code} />
      <input type="hidden" name="taught" value={on ? "on" : "off"} />
      {classes.length > 1 ? (
        <select name="class" aria-label={on ? "Class to mark taught" : "Class to unmark"} className="select min-h-[36px] !w-auto !text-[13px]">
          {classes.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      ) : (
        <input type="hidden" name="class" value={classes[0]} />
      )}
      <button className={on ? "btn secondary" : plain ? "chip" : "btn secondary"} type="submit">
        {on ? "Mark as taught" : "Not taught after all"}
      </button>
    </form>
  );
}
