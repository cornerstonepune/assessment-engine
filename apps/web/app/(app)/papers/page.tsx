import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { ScansTable } from "../capture/scans-table";
import { requireStaff } from "@/lib/auth";
import { choices } from "@/lib/choices";
import { scopeOf } from "@/lib/scope";
import { checkQueue } from "@/lib/queries-read";
import { lastScans } from "@/lib/queries-scans";
import { topics } from "@/lib/queries-people";
import { grades } from "@/lib/queries";
import { actionOf, sigsFor } from "@/lib/assessment-steps";
import { chosenNames, fileLinks, pagesOf } from "@/lib/queries-assessment-extras";
import { assessmentList, KIND_WORDS, paperFilters, paperList, type PaperFilter, type PaperListRow } from "@/lib/queries-papers";
import { weekWords } from "@/lib/week";
import { deadline } from "@/lib/deadline";
import { topicGroups, topicNamesOf } from "@/lib/queries-by-topic";
import { assessmentKey, AssessmentsTable, type Named } from "./assessments-table";
import { ByTopic } from "./by-topic";
import { ghostRow, namedRows } from "./named";
import { countsOf } from "./step-columns";
import { MakeBox } from "./make-box";
import { ReadBox } from "./read-box";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const UUID = /^[0-9a-f-]{36}$/;
const PAGE = (v?: string) => Math.max(1, Math.floor(Number(v)) || 1);

/** What an assessment waits for, as the status filter says it: the one thing its row asks to be done next. */
const STATUS_WORDS: Record<string, string> = {
  approve: "Created, to approve",
  print: "Approved, to print",
  upload: "Printed, to upload",
  reading: "Uploaded, being read",
  check: "Read, to check",
  signoff: "Checked, to sign off",
  results: "Results in",
};

// `view`: the list, or the assessments by topic; `t`: the topic opened there; `tp`: the page of topics.
type Filters = PaperFilter & {
  status?: string;
  view?: string;
  t?: string;
  tp?: string;
};

// An address for the page: every filter, a change laid over them; `open`, the one assessment opened to its children.
function query(f: Filters, change: Partial<Filters> & { open?: string; page?: string } = {}) {
  const q = new URLSearchParams();
  for (const [k, value] of Object.entries({ ...f, ...change })) if (value) q.set(k, value);
  const s = q.toString();
  return s ? `/papers?${s}` : "/papers";
}

const TABS: [string, string][] = [
  ["/papers", "Assessments"],
  ["/capture/check", "Needs checking"],
  ["/capture", "Reading status"],
];

// Assessments (goals/asm_assessments_page.yaml): make one, or read one, and under them the last ten, newest first, each
// named for what it is, its steps in the order the school does them, and the one thing to do next. A row opens to its
// children, each with the same steps and their own pages; nothing about a child's paper is out of reach from here.
export default async function PapersPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const scope = scopeOf(me);
  const taught = (await deadline(topics(scope))).filter((t) => t.shown);
  const f: Filters = {
    class: q.class || undefined,
    child: q.child && UUID.test(q.child) ? q.child : undefined,
    kind: q.kind && q.kind in KIND_WORDS ? q.kind : undefined,
    week: q.week || undefined,
    // only a taught topic narrows the list; any other word is every topic
    topic: taught.some((t) => t.code === q.topic) ? q.topic : undefined,
    set: q.set || undefined,
    subject: q.subject || undefined,
    q: q.q?.trim() || undefined,
    status: q.status && q.status in STATUS_WORDS ? q.status : undefined,
    view: q.view === "topic" ? "topic" : undefined,
    t: q.view === "topic" ? q.t || undefined : undefined,
    tp: q.view === "topic" ? q.tp || undefined : undefined,
  };
  const { status, view, t: openTopic, tp, ...sqlFilter } = f;
  const byTopic = view === "topic";
  // by topic, no topic narrows the list: each topic is a group of its own
  const listFilter = byTopic ? { ...sqlFilter, topic: undefined } : sqlFilter;
  const [groups, { options }, queue, scans, g, { subjects }] = await deadline(
    Promise.all([
      byTopic ? Promise.resolve({ rows: [], more: false, total: 0 }) : assessmentList(listFilter, scope),
      paperFilters(scope),
      checkQueue(scope),
      lastScans(scope),
      grades(),
      choices(),
    ]),
  );
  const topicList = byTopic ? await deadline(topicGroups(listFilter, scope)) : [];
  const open = topicList.find((x) => x.code === openTopic)?.code;
  const topicPage = PAGE(q.page);
  // only the open topic's rows are read, one page of them, with the stage chosen in the database
  const opened_ = open
    ? await deadline(
        assessmentList({ ...listFilter, topic: open }, scope, {
          limit: 10,
          offset: (topicPage - 1) * 10,
          sigs: status ? sigsFor(status as never) : undefined,
        }),
      )
    : null;
  if (opened_) groups.rows.push(...opened_.rows);
  // the newest week first, a paper with no week last; within a week the query's order stands (newest made first)
  groups.rows.sort((a, b) => (a.week && b.week ? b.week.localeCompare(a.week) : a.week ? -1 : b.week ? 1 : 0));
  const keys = groups.rows.map((a) => ({
    key: assessmentKey(a),
    qrs: a.qrs ?? [],
  }));
  const [chosen, files] = await deadline(Promise.all([chosenNames(keys.map((k) => k.key)), fileLinks(keys)]));

  const topicNames = new Map((await deadline(topicNamesOf())).map((t) => [t.code, t.name]));
  const named: Named[] = namedRows(groups.rows, {
    g,
    topicName: (code) => topicNames.get(code) ?? code,
    chosen,
    files: files.byKey,
  });
  const nexts = new Map(named.map((a) => [a, actionOf(countsOf(a), a.waiting).kind]));
  const count = (kind: string) => [...nexts.values()].filter((k) => k === kind).length;
  const rows = status && !byTopic ? named.filter((a) => nexts.get(a) === status) : named;
  // a file that belongs to no assessment is listed first, in red, while no filter hides the assessments around it
  const folded = Object.values({ ...listFilter, status }).some(Boolean);
  const unfiltered = !folded && !byTopic;
  const ghosts: Named[] = unfiltered ? files.unmatched.slice(0, 3).map(ghostRow) : [];

  // the one assessment opened, by its key (kind~class~week~set) — or the one the filters leave — its children with it
  const asked = q.open && q.open.split("~")[0] in KIND_WORDS ? q.open : null;
  const opened = asked ?? (q.open !== "none" && rows.length === 1 ? assessmentKey(rows[0]) : null);
  const [kind, section, week, set] = (opened ?? "").split("~");
  // a child chosen shows their copy under every assessment; otherwise only the one opened has its children read
  const read = await deadline(
    f.child
      ? paperList(listFilter, me.email, scope, "roll")
      : opened
        ? paperList(
            {
              ...listFilter,
              kind,
              class: section || undefined,
              week: week || undefined,
              set: set || undefined,
            },
            me.email,
            scope,
            "roll",
          )
        : Promise.resolve(null),
  );
  const copies = new Map<string, PaperListRow[]>();
  for (const p of read?.rows ?? []) {
    const key = assessmentKey(p);
    if (f.child || key === opened) copies.set(key, [...(copies.get(key) ?? []), p]);
  }
  const pages = await deadline(
    pagesOf(
      [...copies.values()]
        .flat()
        .filter((p) => p.answers > 0)
        .map((p) => p.id),
    ),
  );
  const toCheck = queue.filter((e) => !e.spot).length;
  const here = query(f);
  const subjectWords = new Map(subjects.map((x) => [x.code, x.label] as const));
  const trouble = scans.some((s) => s.status === "error" || s.noCode.length || s.lines.length);

  return (
    <PageShell
      stage="Assessments"
      title="Assessments"
      purpose="Make or read an assessment, then follow each one from created to results in. Its row has the next thing to do."
      action={
        <Link href="/papers/make?kind=assessment&way=same" className="btn">
          Make an assessment
        </Link>
      }
      next={{ href: "/capture/check", label: `${toCheck} answers to check` }}
      details={{
        href: "/capture",
        label: "Scans, and how the reader is doing",
      }}
    >
      <div role="group" aria-label="Assessments tabs" className="mb-3 flex gap-1 border-b border-basalt/15">
        {TABS.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            aria-current={href === "/papers" ? "page" : undefined}
            className={`-mb-px border border-b-0 px-4 py-2 text-[14px] no-underline ${href === "/papers" ? "border-basalt/30 bg-chalk font-semibold text-basalt" : "border-transparent text-basalt/65 hover:text-basalt"}`}
          >
            {label}
          </Link>
        ))}
      </div>
      <div className="mb-[18px] grid items-stretch gap-[14px] lg:grid-cols-2" data-ux="blocks">
        <MakeBox />
        <ReadBox read={q.read} why={q.why} pages={q.pages} reading={scans.some((s) => s.status === "running")} />
      </div>
      {q.said ? (
        <p role="status" className="mb-3 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]">
          {q.said}
        </p>
      ) : null}

      <div role="group" aria-label="Show the assessments" className="mb-2 flex gap-2" data-views>
        {(
          [
            ["list", "All assessments"],
            ["topic", "By topic"],
          ] as const
        ).map(([v, label]) => (
          <Link
            key={v}
            href={query(f, {
              view: v === "topic" ? "topic" : undefined,
              t: undefined,
              tp: undefined,
              page: undefined,
              open: undefined,
            })}
            aria-current={(v === "topic") === byTopic ? "page" : undefined}
            className={`chip no-underline ${(v === "topic") === byTopic ? "on" : ""}`}
          >
            {label}
          </Link>
        ))}
      </div>
      <FilterBar
        action="/papers"
        keep={{ set: f.set, child: f.child, view, t: open }}
        filters={[
          {
            name: "class",
            label: "Class",
            value: f.class,
            all: "Every class",
            options: options.classes.map((c) => [c, c] as const),
          },
          // by topic, each topic is a group of its own: no topic to pick
          ...(byTopic
            ? []
            : [
                {
                  name: "topic",
                  label: "Topic",
                  value: f.topic,
                  all: "Every topic",
                  options: taught.map((t) => [t.code, t.name] as const),
                },
              ]),
          {
            name: "subject",
            label: "Subject",
            value: f.subject,
            all: "Every subject",
            options: subjects.map((s) => [s.code, s.label] as const),
          },
          {
            name: "kind",
            label: "Kind",
            value: f.kind,
            all: "Any kind",
            options: Object.entries(KIND_WORDS),
          },
          {
            name: "week",
            label: "Week",
            value: f.week,
            all: "Every week",
            options: options.weeks.map((w) => [w, weekWords(w)] as const),
          },
          {
            name: "status",
            label: "Stage",
            value: f.status,
            all: "Any stage",
            options: byTopic
              ? Object.entries(STATUS_WORDS)
              : Object.entries(STATUS_WORDS)
                  .filter(([k]) => count(k) || f.status === k)
                  .map(([k, w]) => [k, `${w} (${count(k)})`] as const),
          },
        ]}
        search={{ name: "q", value: f.q, placeholder: "Find an assessment" }}
      />

      <section aria-label="Papers">
        {byTopic ? (
          <>
            <ByTopic
              groups={topicList}
              subjects={subjectWords}
              open={open}
              rows={rows}
              of={opened_?.total ?? 0}
              copies={copies}
              pages={pages}
              page={topicPage}
              topicPage={PAGE(tp)}
              back={here}
              topicHref={(code, isOpen) =>
                query(f, {
                  t: isOpen ? undefined : code,
                  page: undefined,
                  open: undefined,
                })
              }
              assessmentHref={(a, isOpen) => query(f, { open: isOpen ? "none" : assessmentKey(a) })}
              assessmentsPageHref={(n) => query(f, { page: String(n) })}
              topicsPageHref={(n) => query(f, { tp: String(n), t: undefined, page: undefined })}
            />
            {topicList.length === 0 ? (
              <p className="note mt-2">{folded ? "Nothing matches these filters." : "No assessments yet."}</p>
            ) : null}
          </>
        ) : (
          <>
            <AssessmentsTable
              rows={[...ghosts, ...rows]}
              copies={copies}
              pages={pages}
              page={PAGE(q.page)}
              back={here}
              href={(a, open) => query(f, { open: open ? "none" : assessmentKey(a) })}
              pageHref={(n) => query(f, { page: String(n) })}
            />
            {rows.length === 0 && ghosts.length === 0 ? (
              <p className="note mt-2">{folded ? "Nothing matches these filters." : "No assessments yet."}</p>
            ) : null}
            {groups.more ? <p className="note mt-2">The newest 300 assessments are shown; narrow the filters to see the rest.</p> : null}
          </>
        )}
      </section>

      {scans.length ? (
        <section aria-label="Read a scan" className="mt-4">
          <details open={trouble} data-files-read>
            <summary className="cursor-pointer text-[13.5px]">Files read lately, and what each lacks ({scans.length})</summary>
            <div className="mt-2">
              <ScansTable scans={scans} from="/papers" />
            </div>
          </details>
        </section>
      ) : null}
      <details className="mt-3 text-[13px] text-basalt/75">
        <summary className="cursor-pointer">How it works</summary>
        <p className="mt-1">
          An assessment is named from the topic and level printed on its paper; rename it on its row. A scan goes to the assessment its
          printed codes belong to. Home assessments wait for your approval, one row at a time.
        </p>
      </details>
    </PageShell>
  );
}
