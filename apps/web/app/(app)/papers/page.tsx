import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { choices } from "@/lib/choices";
import { scopeOf } from "@/lib/scope";
import { checkQueue } from "@/lib/queries-read";
import { lastScans } from "@/lib/queries-scans";
import { topics } from "@/lib/queries-people";
import {
  assessmentList,
  givenOn,
  KIND_WORDS,
  paperFilters,
  paperList,
  STAGE_WORDS,
  STAGES,
  type PaperFilter,
  type PaperListRow,
} from "@/lib/queries-papers";
import { weekWords } from "@/lib/week";
import { deadline } from "@/lib/deadline";
import { ReadScan } from "../capture/read-scan";
import { assessmentKey, AssessmentsTable } from "./assessments-table";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// The four ways an educator makes an assessment (goals/ui2-assessments.yaml), each opening the maker ready for that use.
// Nimish, 2026-10-11: "for every child, there is a customized assessment and the capability to create their own
// assessments or generate assessments as and when required for a particular class".
const STARTS: [string, string, string][] = [
  ["For a class", "/papers/make?kind=assessment&way=same", "one assessment for every child of a class: choose the class, then a topic or the skills"],
  ["For each child", "/make", "this week's home assessment for each child, made from their own record, to approve"],
  ["For one child", "/papers/make?kind=assessment&way=own&one=1", "a follow-up for one child: the engine proposes their next step, and you can change it"],
  ["A ready-made worksheet", "/worksheets", "a worksheet from the library, printed for the children you choose"],
];

const UUID = /^[0-9a-f-]{36}$/;
const PAGE = (v?: string) => Math.max(1, Math.floor(Number(v)) || 1);

// An address for the page: every filter, a change laid over them; `open`, the one assessment opened to its copies.
function query(f: PaperFilter, change: Partial<PaperFilter> & { open?: string; page?: string } = {}) {
  const q = new URLSearchParams();
  for (const [k, value] of Object.entries({ ...f, ...change })) if (value) q.set(k, value);
  const s = q.toString();
  return s ? `/papers?${s}` : "/papers";
}

// Assessments (goals/u9-papers.yaml, goals/ui5-assessments-readable.yaml, goals/ux5-papers-grouped.yaml): its weeks,
// newest first, the newest open, each one line saying what waits in it; each assessment a line that opens in place to
// its copies in roll order — one the filters leave alone opens by itself. Filtered by topic and stage at the top, by
// class, child, kind and week in a fold; a filter chosen opens every week it leaves, and a child chosen shows their copy
// under each assessment. Reading a scan, the
// queue of answers to check, and making an assessment start here.
export default async function PapersPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const taught = (await deadline(topics(scopeOf(me)))).filter((t) => t.shown);
  const f: PaperFilter = {
    class: q.class || undefined,
    child: q.child && UUID.test(q.child) ? q.child : undefined,
    kind: q.kind && q.kind in KIND_WORDS ? q.kind : undefined,
    week: q.week || undefined,
    stage: q.stage && (STAGES as readonly string[]).includes(q.stage) ? q.stage : undefined,
    // only a taught topic narrows the list; any other word is every topic
    topic: taught.some((t) => t.code === q.topic) ? q.topic : undefined,
    set: q.set || undefined,
    subject: q.subject || undefined,
    q: q.q?.trim() || undefined,
  };
  const [groups, { stages, options }, queue, scans] = await deadline(
    Promise.all([assessmentList(f, scopeOf(me)), paperFilters(f, me.email, scopeOf(me)), checkQueue(scopeOf(me)), lastScans(scopeOf(me))]),
  );
  // the one assessment opened, by its key (kind~class~week~set) — or the one the filters leave — its copies with it
  const asked = q.open && q.open.split("~")[0] in KIND_WORDS ? q.open : null;
  // `none`: the one left alone, closed by hand, stays closed
  const opened = asked ?? (q.open !== "none" && groups.rows.length === 1 ? assessmentKey(groups.rows[0]) : null);
  const [kind, section, week, set] = (opened ?? "").split("~");
  // a child chosen shows their copy under every assessment; otherwise only the one opened has its copies read
  const read = await deadline(
    f.child
      ? paperList(f, me.email, scopeOf(me), "roll")
      : opened
        ? paperList({ ...f, kind, class: section || undefined, week: week || undefined, set: set || undefined }, me.email, scopeOf(me), "roll")
        : Promise.resolve(null),
  );
  const copies = new Map<string, PaperListRow[]>();
  for (const p of read?.rows ?? []) {
    const key = assessmentKey(p);
    if (f.child || key === opened) copies.set(key, [...(copies.get(key) ?? []), p]);
  }
  const toCheck = queue.filter((e) => !e.spot).length;
  const [{ subjects }, given] = await Promise.all([choices(), givenOn(groups.rows)]);
  const folded = !!(f.class || f.child || f.kind || f.week || f.subject || f.q || f.stage || f.topic || f.set);
  const stageOptions = STAGES.filter((s) => s !== "replaced" || stages[s] || f.stage === s).map((s) => [s, `${STAGE_WORDS[s][0].toUpperCase()}${STAGE_WORDS[s].slice(1)} (${stages[s]})`] as const);

  return (
    <PageShell
      stage="Assessments"
      title="Assessments"
      purpose="Make an assessment, then follow each one from approval to done. A row opens to its copies; a copy opens to print or to check."
      action={
        <Link href="/papers/make?kind=assessment&way=same" className="btn">
          Make an assessment
        </Link>
      }
      next={{ href: "/capture/check", label: `${toCheck} answers to check` }}
      details={{ href: "/capture", label: "Scans, and how the reader is doing" }}
    >
      {/* the upload box at the top (goals/s2-the-assessment-card.yaml): papers in is the day's first job */}
      <div className="mb-[18px]">
        <ReadScan from="/papers" read={q.read} why={q.why} pages={q.pages} scans={scans} />
      </div>
      <section aria-label="Make an assessment" className="mb-[18px]">
        <h2 className="label mb-2">Make an assessment</h2>
        <div className="grid gap-[10px] sm:grid-cols-2 xl:grid-cols-4">
          {STARTS.map(([title, href, words]) => (
            <Link key={title} href={href} className="panel flex flex-col gap-1 p-4 text-basalt no-underline hover:border-basalt">
              <span className="font-heading text-[16px]">{title}</span>
              <span className="text-[13px] text-basalt/65">{words}</span>
            </Link>
          ))}
        </div>
      </section>

      <FilterBar
        action="/papers"
        keep={{ topic: f.topic, set: f.set, child: f.child }}
        filters={[
          { name: "class", label: "Class", value: f.class, all: "Every class", options: options.classes.map((c) => [c, c] as const) },
          { name: "subject", label: "Subject", value: f.subject, all: "Every subject", options: subjects.map((s) => [s.code, s.label] as const) },
          { name: "kind", label: "Kind", value: f.kind, all: "Any kind", options: Object.entries(KIND_WORDS) },
          { name: "week", label: "Week", value: f.week, all: "Every week", options: options.weeks.map((w) => [w, weekWords(w)] as const) },
          { name: "stage", label: "Status", value: f.stage, all: "Any status", options: stageOptions },
        ]}
        search={{ name: "q", value: f.q, placeholder: "Find an assessment" }}
      />

      <section aria-label="Papers">
        <AssessmentsTable
          rows={groups.rows}
          copies={copies}
          page={PAGE(q.page)}
          subjects={new Map(subjects.map((s) => [s.code, s.label]))}
          given={given}
          href={(a, open) => query(f, { open: open ? "none" : assessmentKey(a) })}
          pageHref={(n) => query(f, { page: String(n) })}
        />
        {groups.rows.length === 0 ? <p className="note mt-2">{folded ? "Nothing matches these filters." : "No assessments yet."}</p> : null}
        {groups.more ? <p className="note mt-2">The newest 300 assessments are shown; narrow the filters to see the rest.</p> : null}
      </section>
    </PageShell>
  );
}
