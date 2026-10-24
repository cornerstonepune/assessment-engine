import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { StatusChip } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { choices } from "@/lib/choices";
import { deadline } from "@/lib/deadline";
import { questionKinds } from "@/lib/question-types";
import { queueByWeek, trustNow } from "@/lib/queries-today";
import { tasksFor } from "@/lib/queries-todo";
import { scopeOf } from "@/lib/scope";
import { filterTasks, groupTasks, KINDS, type Kind, type Task, waitingCount } from "@/lib/todo";
import { TABLE_ROW_LIMIT, type Column } from "@/lib/ux-rules";
import { subjectsFor } from "@/lib/viewing";
import { noteLines, weekNote } from "@/lib/queries-week-note";
import { isoWeek, weekWords } from "@/lib/week";
import { Shrinking } from "./shrinking";

// What needs doing (goals/nav_teacher_scope_and_todo.yaml; it was Today, and keeps its address). Nimish, 24 Oct 2026: "all
// of these pages, like the Today page, need to be converted into a nice, well-positioned, aesthetically pleasing table ...
// Key things that need to happen should be in a simple table with some red, amber, green notation ... Everything has to have
// its own set of approvals." One row is one thing on one item, with one button that opens exactly that item: there is no
// button over every row. Grouped by subject, then topic, each folded open or shut; red first. In the person's subjects and
// classes (lib/viewing.ts, lib/scope.ts), and only the decisions that are theirs.
const COLUMNS: Column<Task>[] = [
  { key: "priority", label: "Priority", status: true, width: "9rem", keep: true, value: (t) => t.state, cell: (t) => <StatusChip state={t.state} /> },
  { key: "what", label: "What", width: "15rem", value: (t) => t.what },
  { key: "where", label: "Where", value: (t) => t.where },
  { key: "many", label: "How many", width: "8rem", value: (t) => t.many },
  { key: "action", label: "", width: "12rem", keep: true, value: (t) => t.action, cell: (t) => <Link href={t.href} className="btn secondary whitespace-nowrap" data-action={t.kind}>{t.action}</Link> },
];

type Q = Record<string, string | undefined>;
const address = (q: Q, change: Q = {}) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...q, ...change })) if (v) p.set(k, v);
  const s = p.toString();
  return s ? `/today?${s}` : "/today";
};

export default async function WhatNeedsDoing({ searchParams }: { searchParams: Promise<Q> }) {
  const q = await searchParams;
  const me = await requireStaff();
  const [all, offered, weeks, trust, { words }] = await deadline(Promise.all([tasksFor(me), choices(), queueByWeek(scopeOf(me)), trustNow(), questionKinds()]));
  const mine = subjectsFor(me, offered.subjects);
  const label = (c: string | null) => offered.subjects.find((s) => s.code === c)?.label ?? c ?? "";
  // each page starts at the person's own scope: the subject chosen in the Viewing control, else every subject of theirs
  const subject = mine.find((s) => s.code === q.subject)?.code ?? (me.subject && mine.some((s) => s.code === me.subject) && mine.length > 1 ? me.subject : undefined);
  const mySubjects = mine.map((s) => s.code);
  const known = await deadline(weekNote(scopeOf(me), subject ?? mine[0]?.code ?? ""));
  const inView = filterTasks(all, {}, mySubjects);
  const topic = inView.some((t) => t.topic === q.topic) ? q.topic : undefined;
  const kind = (Object.keys(KINDS) as Kind[]).find((k) => k === q.kind);
  const tasks = filterTasks(all, { subject, topic, kind }, mySubjects);
  const groups = groupTasks(tasks, label);
  const topics = [...new Map(inView.filter((t) => t.topic).map((t) => [t.topic!, t.topicName!])).entries()];
  const first = tasks.find((t) => t.state === "doNow") ?? tasks[0];
  const page = Math.max(1, Number(q.page) || 1);
  return (
    <PageShell
      stage="What needs doing"
      title="What needs doing"
      purpose="Everything that waits on you, red first. Each row has its own button that opens that one thing."
      action={
        <Link href={first?.href ?? "/taught"} className="btn">
          {first ? `Start with: ${first.what.toLowerCase()} →` : "Open Teaching →"}
        </Link>
      }
      next={{ href: "/taught", label: "Teaching" }}
    >
      <FilterBar
        action="/today"
        filters={[
          { name: "subject", label: "Subject", value: subject, all: "Every subject", options: mine.map((s) => [s.code, s.label] as const) },
          { name: "topic", label: "Topic", value: topic, all: "Every topic", options: topics },
          { name: "kind", label: "What", value: kind, all: "Everything", options: (Object.keys(KINDS) as Kind[]).map((k) => [k, KINDS[k].what] as const) },
        ]}
      />
      {tasks.length === 0 ? <EmptyState next={{ href: "/taught", label: "Teaching" }}>Nothing waits on you{subject || topic || kind ? " under these choices" : ""}.</EmptyState> : null}
      <div className="grid gap-4">
        {groups.map((s) => {
          const all = s.topics.flatMap((t) => t.tasks);
          const todo = waitingCount(all);
          const later = all.length - todo;
          return (
          <details key={s.subject} open className="panel" data-subject={s.subject}>
            <summary className="panel-head cursor-pointer">
              <h2 className="text-[16px]">{s.subject}</h2>
              <span className="fact text-[11px] text-basalt/55" data-todo={todo}>
                {todo} to do{later ? ` · ${later} when ready` : ""}
              </span>
            </summary>
            <div className="panel-body grid gap-3">
              {s.topics.map((t, at) => {
                const reds = t.tasks.filter((x) => x.state === "doNow").length;
                const filtered = Boolean(topic);
                const shown = filtered ? t.tasks : t.tasks.slice(0, TABLE_ROW_LIMIT);
                return (
                  <details key={t.topic} open={at < 3 || reds > 0 || filtered} data-topic={t.topic}>
                    <summary className="cursor-pointer text-[14px] font-medium">
                      {t.topic} <span className="fact ml-2 text-basalt/55">{t.tasks.length} {t.tasks.length === 1 ? "row" : "rows"}</span>
                      {reds ? <span className="ml-2 inline-block align-middle"><StatusChip state="doNow" note={String(reds)} /></span> : null}
                    </summary>
                    <div className="mt-2 min-w-0">
                      <DataTable
                        label={`${s.subject} · ${t.topic}`}
                        columns={COLUMNS}
                        rows={shown}
                        rowKey={(x) => x.id}
                        extras={{ attrs: (x) => ({ "data-kind": x.kind, "data-state": x.state }) }}
                        more={{ page, href: (n: number) => address(q, { page: String(n) }) }}
                      />
                      {!filtered && t.tasks.length > TABLE_ROW_LIMIT ? (
                        <p className="note mt-1">
                          {t.tasks.length - TABLE_ROW_LIMIT} more · <Link href={address(q, { subject: subject ?? mine.find((m) => label(m.code) === s.subject)?.code, topic: t.tasks[0].topic ?? undefined })}>Show all →</Link>
                        </p>
                      ) : null}
                    </div>
                  </details>
                );
              })}
            </div>
          </details>
          );
        })}
      </div>
      {/* what the system now knows this week, five lines (goals/s1-subject-class-and-today.yaml): folded, under the table, not above it */}
      <details className="panel mt-6 p-4" data-know>
        <summary className="cursor-pointer font-heading text-[17px]">What the system now knows</summary>
        <p className="mt-1 text-[12.5px] text-basalt/62">
          {offered.subjects.find((x) => x.code === (subject ?? mine[0]?.code))?.label ?? "Every subject"}, {weekWords(isoWeek())}, in the classes you see
        </p>
        <ol className="mt-2 grid list-decimal gap-1 pl-5 text-[14px] leading-snug">
          {noteLines(known).map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ol>
      </details>
      <div className="mt-6">
        <Shrinking weeks={weeks} trust={trust} words={words} page={Number(q.weeks) || 1} />
      </div>
    </PageShell>
  );
}
