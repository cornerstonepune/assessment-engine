import Link from "@/components/link";
import { Body, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { checkQueue } from "@/lib/queries-read";
import { topics } from "@/lib/queries-people";
import {
  assessmentList,
  KIND_WORDS,
  paperFilters,
  paperList,
  STAGE_WORDS,
  STAGES,
  type AssessmentRow,
  type PaperFilter,
} from "@/lib/queries-papers";
import { weekWords } from "@/lib/week";
import { deadline } from "@/lib/deadline";
import { ReadScan } from "../capture/read-scan";
import { AssessmentsTable } from "./assessments-table";
import { PapersTable } from "./papers-table";

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
type View = "assessments" | "papers";

// An address for the page: the view first, then every filter, a change laid over them.
function query(f: PaperFilter, view: View, change: Partial<PaperFilter> = {}) {
  const q = new URLSearchParams();
  if (view === "papers") q.set("view", "papers");
  for (const [k, value] of Object.entries({ ...f, ...change })) if (value) q.set(k, value);
  const s = q.toString();
  return s ? `/papers?${s}` : "/papers";
}

function Select({ name, label, value, all, options }: {
  name: string; label: string; value?: string; all: string; options: [string, string][];
}) {
  return (
    <label className="field min-w-[11rem]">
      <span className="label">{label}</span>
      <select className="select" name={name} defaultValue={value ?? ""}>
        <option value="">{all}</option>
        {options.map(([v, words]) => <option key={v} value={v}>{words}</option>)}
      </select>
    </label>
  );
}

// Assessments (goals/u9-papers.yaml, goals/ui5-assessments-readable.yaml): one row for each assessment, its copies
// counted by stage, or every paper on its own; filtered by topic, stage, class, child, kind and week; an assessment
// opens its copies. Reading a scan, the queue of answers to check, and making an assessment start here.
export default async function PapersPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const view: View = q.view === "papers" ? "papers" : "assessments";
  const taught = (await deadline(topics(scopeOf(me)))).filter((t) => t.taught);
  const f: PaperFilter = {
    class: q.class || undefined,
    child: q.child && UUID.test(q.child) ? q.child : undefined,
    kind: q.kind && q.kind in KIND_WORDS ? q.kind : undefined,
    week: q.week || undefined,
    stage: q.stage && (STAGES as readonly string[]).includes(q.stage) ? q.stage : undefined,
    // only a taught topic narrows the list; any other word is every topic
    topic: taught.some((t) => t.code === q.topic) ? q.topic : undefined,
    set: q.set || undefined,
  };
  const [papers, groups, { stages, options }, queue] = await deadline(
    Promise.all([
      view === "papers" ? paperList(f, me.email, scopeOf(me)) : null,
      view === "assessments" ? assessmentList(f, scopeOf(me)) : null,
      paperFilters(f, me.email, scopeOf(me)),
      checkQueue(scopeOf(me)),
    ]),
  );
  const shown = groups ?? papers;
  const toCheck = queue.filter((e) => !e.spot).length;
  const all = STAGES.reduce((n, s) => n + stages[s], 0);
  // an assessment opens its copies: its class, week, kind and skill set or worksheet, under the other filters
  const copies = (a: AssessmentRow) =>
    query(f, "papers", { class: a.section ?? undefined, week: a.week ?? undefined, kind: a.kind, set: a.set ?? undefined });

  return (
    <>
      <PageHeader
        stage="Assessments"
        title="Assessments"
        sub="Make an assessment, then follow every one from approval to done, by topic or all together. An assessment opens its copies; a paper opens to print it, or to check its answers once it is read."
      />
      <Body>
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
        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          <Link href="/capture/check" className="btn secondary">
            {toCheck} answers to check →
          </Link>
          <Link href="/capture" className="text-[13px] md:ml-auto">
            Scans, and how the reader is doing
          </Link>
        </div>

        <nav aria-label="View" className="mb-3 flex flex-wrap gap-2">
          {(["assessments", "papers"] as const).map((v) => (
            <Link
              key={v}
              href={query({ ...f, set: v === "assessments" ? undefined : f.set }, v)}
              className={`chip ${view === v ? "on" : ""}`}
              aria-current={view === v ? "page" : undefined}
            >
              {v === "assessments" ? "By assessment" : "Each paper"}
            </Link>
          ))}
        </nav>

        <nav aria-label="Topic" className="mb-3 flex flex-wrap gap-2">
          <Link href={query(f, view, { topic: undefined })} className={`chip ${!f.topic ? "on" : ""}`} aria-current={!f.topic ? "page" : undefined}>
            All topics
          </Link>
          {taught.map((t) => (
            <Link
              key={t.code}
              href={query(f, view, { topic: t.code })}
              className={`chip ${f.topic === t.code ? "on" : ""}`}
              aria-current={f.topic === t.code ? "page" : undefined}
            >
              {t.name}
            </Link>
          ))}
        </nav>

        <nav aria-label="Papers by stage" className="mb-3 flex flex-wrap gap-2">
          <Link href={query(f, view, { stage: undefined })} className={`chip ${!f.stage ? "on" : ""}`}
            aria-current={!f.stage ? "page" : undefined}>
            Every stage <span className="fact ml-1 opacity-70">{all}</span>
          </Link>
          {STAGES.map((s) => (
            <Link key={s} href={query(f, view, { stage: s })} className={`chip ${f.stage === s ? "on" : ""}`}
              aria-current={f.stage === s ? "page" : undefined}>
              {STAGE_WORDS[s][0].toUpperCase() + STAGE_WORDS[s].slice(1)} <span className="fact ml-1 opacity-70">{stages[s]}</span>
            </Link>
          ))}
        </nav>

        <form action="/papers" className="panel mb-[18px] flex flex-wrap items-end gap-3 p-4">
          {view === "papers" ? <input type="hidden" name="view" value="papers" /> : null}
          {f.stage ? <input type="hidden" name="stage" value={f.stage} /> : null}
          {f.topic ? <input type="hidden" name="topic" value={f.topic} /> : null}
          <Select name="class" label="Class" value={f.class} all="Every class" options={options.classes.map((c) => [c, c])} />
          <Select name="child" label="Child" value={f.child} all="Every child" options={options.children.map((c) => [c.id, c.label])} />
          <Select name="kind" label="Kind" value={f.kind} all="Any kind" options={Object.entries(KIND_WORDS)} />
          <Select name="week" label="Week" value={f.week} all="Every week" options={options.weeks.map((w) => [w, weekWords(w)])} />
          <button type="submit" className="btn">Show</button>
          {f.class || f.child || f.kind || f.week || f.stage || f.topic || f.set ? (
            <Link href={view === "papers" ? "/papers?view=papers" : "/papers"} className="text-[13px]">Clear</Link>
          ) : null}
        </form>

        <section className="panel" aria-label="Papers">
          <div className="overflow-x-auto">
            {groups ? <AssessmentsTable rows={groups.rows} opens={copies} /> : null}
            {papers ? <PapersTable rows={papers.rows} /> : null}
          </div>
          {shown?.rows.length === 0 ? <p className="note p-4">Nothing matches these filters.</p> : null}
          {shown?.more ? <p className="note p-4">The newest 300 are shown; narrow the filters to see the rest.</p> : null}
        </section>

        <div className="mt-[18px]">
          <ReadScan from="/papers" read={q.read} why={q.why} pages={q.pages} />
        </div>
      </Body>
    </>
  );
}
