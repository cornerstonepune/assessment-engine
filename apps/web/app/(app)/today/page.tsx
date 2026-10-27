import Link from "@/components/link";
import { Count } from "@/components/count";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { TaughtNotice } from "@/components/taught-notice";
import { StatusChip } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { choices } from "@/lib/choices";
import { deadline } from "@/lib/deadline";
import { tasksFor } from "@/lib/queries-todo";
import { isMine, scopeOf } from "@/lib/scope";
import { count, filterTasks, KINDS, sectionsOf, TODO_GROUPS, type Kind, type Section, type Task, waitingCount } from "@/lib/todo";
import type { Column } from "@/lib/ux-rules";
import { subjectsFor } from "@/lib/viewing";
import { noteLines, weekNote } from "@/lib/queries-week-note";
import { isoWeek, weekWords } from "@/lib/week";
import { switchTopic } from "../topic-actions";

// What needs doing (goals/nav3_what_needs_doing.yaml; it was Today, and keeps its address). Nimish, 26 Oct 2026: "When I go to
// What Needs Doing, everything opens up like a huge table. Can we have proper expand/collapse, and different types of things that
// you need to do ... skills to be checked or topics to be marked. The actual actionables that they need to do are there, and then
// it expands as a table. Everything is very well sequenced with clarity." So: a short list of groups, one line each (the kind of
// task, how many, red/amber/green, the next action), each folded until opened into its own table, in the order the work happens
// (lib/todo.ts `TODO_GROUPS`). A row has its own action and there is no button over every row. Each group's heading opens the page
// that does that kind of work. In the person's subjects and classes (lib/viewing.ts, lib/scope.ts); the page's own filters narrow it.
const COLUMNS = (mixed: boolean): Column<Task>[] => [
  { key: "priority", label: "Priority", status: true, width: "9rem", keep: true, value: (t) => t.state, cell: (t) => <StatusChip state={t.state} /> },
  ...(mixed ? [{ key: "what", label: "What", width: "13rem", value: (t: Task) => t.what }] : []),
  { key: "where", label: "Where", value: (t) => t.where },
  { key: "many", label: "How many", width: "8rem", value: (t) => t.many },
  { key: "action", label: "", width: "16rem", keep: true, value: (t) => t.action, cell: (t) => <RowAction t={t} /> },
];

/** The row's one action: a button that opens that one item; a topic is marked taught in the row itself, for the class it names. */
function RowAction({ t }: { t: Task }) {
  if (t.kind !== "taught") return <Link href={t.href} className="btn secondary whitespace-nowrap" data-action={t.kind}>{t.action}</Link>;
  return (
    <form action={switchTopic} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={t.id.slice("taught:".length)} />
      <input type="hidden" name="taught" value="on" />
      {t.sections.length > 1 ? (
        <select name="class" aria-label={`Class taught ${t.topicName}`} className="select min-h-[36px] !w-auto !text-[13px]">
          {t.sections.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      ) : (
        <input type="hidden" name="class" value={t.sections[0]} />
      )}
      <button className="btn secondary whitespace-nowrap" type="submit" data-action={t.kind}>
        {t.action}
      </button>
    </form>
  );
}

type Q = Record<string, string | undefined>;
const address = (q: Q, change: Q = {}) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...q, ...change })) if (v) p.set(k, v);
  const s = p.toString();
  return s ? `/today?${s}` : "/today";
};
const SECTION_ORDER = (a: string, b: string) => a.localeCompare(b, "en", { numeric: true });

export default async function WhatNeedsDoing({ searchParams }: { searchParams: Promise<Q> }) {
  const q = await searchParams;
  const me = await requireStaff();
  const [all, offered] = await deadline(Promise.all([tasksFor(me), choices()]));
  const mine = subjectsFor(me, offered.subjects);
  const mySubjects = mine.map((s) => s.code);
  // what waits on this person, and the one count the menu carries; the page's filters narrow what is listed, never that figure
  const here = filterTasks(all, {}, mySubjects);
  const classes = [...new Set(here.flatMap((t) => t.sections))].sort(SECTION_ORDER);
  const subject = mine.find((s) => s.code === q.subject)?.code;
  const section = classes.find((c) => c === q.class);
  const group = TODO_GROUPS.find((g) => g.key === q.group)?.key;
  // `kind` is the address the page had before it had groups (a bookmark, a link in a message): one kind of task, so one group
  const kind = (Object.keys(KINDS) as Kind[]).find((k) => k === q.kind);
  const tasks = filterTasks(here, { subject, section, kind }, mySubjects).filter((t) => !group || TODO_GROUPS.find((g) => g.key === group)!.kinds.includes(t.kind));
  // with a class chosen, a topic is marked taught for that class alone
  const narrowed = section ? tasks.map((t) => (t.kind === "taught" ? { ...t, sections: [section], where: t.where.replace(/ · [^·]*$/, ` · ${section}`), many: count(1, "class", "classes") } : t)) : tasks;
  const sections = sectionsOf(narrowed);
  // the note under the list is read for the class chosen in the page's own filter, else for all the person's classes
  const scope = scopeOf(me);
  const known = await deadline(weekNote(q.class && isMine(scope, q.class) ? { classes: [q.class], note: null } : scope, subject ?? mine[0]?.code ?? ""));
  const waiting = waitingCount(here);
  const first = here.find((t) => t.state === "doNow") ?? here[0];
  // one group left (a kind asked for, a filter) is the open one, and the page number is its own
  const open = TODO_GROUPS.find((g) => g.key === q.open)?.key ?? (sections.length === 1 ? sections[0].group.key : undefined);
  const page = Math.max(1, Number(q.page) || 1);
  return (
    <PageShell
      stage="What needs doing"
      title="What needs doing"
      purpose="The kinds of work waiting on you, in the order the week runs. Open one to see its rows; each row has its own button."
      action={
        <Link href={first?.href ?? "/papers"} className="btn">
          {first ? `Start with: ${first.what.toLowerCase()} →` : "Open Assessments →"}
        </Link>
      }
      next={{ href: "/papers", label: "Assessments" }}
    >
      <TaughtNotice q={q} />
      <p className="mb-3 text-[14px]" data-todo={waiting}>
        <Count of="What needs doing" n={waiting} /> to do{here.length > waiting ? ` · ${here.length - waiting} when ready` : ""}
      </p>
      <FilterBar
        action="/today"
        filters={[
          ...(mine.length > 1 ? [{ name: "subject", label: "Subject", value: subject, all: "Every subject", options: mine.map((s) => [s.code, s.label] as const) }] : []),
          ...(classes.length > 1 ? [{ name: "class", label: "Class", value: section, all: "Every class", options: classes.map((c) => [c, c] as const) }] : []),
          { name: "group", label: "What", value: group, all: "Everything", options: TODO_GROUPS.map((g) => [g.key, g.title] as const) },
        ]}
      />
      {sections.length === 0 ? <EmptyState next={{ href: "/papers", label: "Assessments" }}>Nothing waits on you{subject || section || group || kind ? " under these choices" : ""}.</EmptyState> : null}
      <ol className="grid gap-2" aria-label="Kinds of work waiting">
        {sections.map((s) => (
          <Group key={s.group.key} s={s} open={s.group.key === open} page={s.group.key === open ? page : 1} q={q} />
        ))}
      </ol>
      {/* what the system now knows this week, five lines (goals/s1-subject-class-and-today.yaml): folded, under the list */}
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
    </PageShell>
  );
}

/** One kind of work: a line (heading to its page, how many, red/amber/green, the next action), folded into its own table. */
function Group({ s, open, page, q }: { s: Section; open: boolean; page: number; q: Q }) {
  const { group, tasks, next } = s;
  const mixed = new Set(tasks.map((t) => t.kind)).size > 1;
  return (
    <li className="min-w-0">
      <details open={open} className="group panel" data-group={group.key}>
        <summary className="flex min-h-12 cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2">
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" className="shrink-0 text-basalt/55 transition-transform group-open:rotate-90">
            <path d="M6 3l5 5-5 5" />
          </svg>
          <h2 className="min-w-0 flex-1 text-[16px]">
            <Link href={group.home} data-group-home>
              {group.title}
            </Link>
          </h2>
          <span className="fact w-28 text-right text-[13px]" data-group-count={tasks.length}>
            {count(tasks.length, ...group.of)}
          </span>
          <span className="w-32">
            <StatusChip state={s.state} />
          </span>
          <span className="w-[17rem] text-right max-md:w-full max-md:text-left">
            <Link href={next.href} className="btn secondary whitespace-nowrap" data-next>
              Next: {next.action.toLowerCase()}
            </Link>
          </span>
        </summary>
        <div className="min-w-0 px-4 pb-4">
          <DataTable
            label={group.title}
            columns={COLUMNS(mixed)}
            rows={tasks}
            rowKey={(x) => x.id}
            extras={{ attrs: (x) => ({ "data-kind": x.kind, "data-state": x.state, "data-shows": x.shows }) }}
            more={{ page, href: (n: number) => address(q, { open: group.key, page: n > 1 ? String(n) : undefined }) }}
          />
        </div>
      </details>
    </li>
  );
}
