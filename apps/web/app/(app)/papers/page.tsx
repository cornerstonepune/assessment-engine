import Link from "@/components/link";
import { Body, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { checkQueue } from "@/lib/queries-read";
import { lastScans } from "@/lib/queries-scans";
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
  type PaperListRow,
} from "@/lib/queries-papers";
import { weekWords } from "@/lib/week";
import { deadline } from "@/lib/deadline";
import { ReadScan } from "../capture/read-scan";
import { assessmentKey, AssessmentsTable } from "./assessments-table";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// The four ways an educator makes an assessment (goals/ui2-assessments.yaml), each opening the maker ready for that use,
// all behind one button (goals/s2b-assessments-declutter.yaml). Nimish, 2026-10-11: "for every child, there is a
// customized assessment and the capability to create their own assessments or generate assessments as and when required
// for a particular class".
const STARTS: [string, string][] = [
  ["For a class", "/papers/make?kind=assessment&way=same"],
  ["For each child", "/make"],
  ["For one child", "/papers/make?kind=assessment&way=own&one=1"],
  ["A ready-made worksheet", "/worksheets"],
];

const UUID = /^[0-9a-f-]{36}$/;

// An address for the page: every filter, a change laid over them; `open`, the one assessment opened to its copies.
function query(f: PaperFilter, change: Partial<PaperFilter> & { open?: string } = {}) {
  const q = new URLSearchParams();
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
  const chosen = !!(f.class || f.child || f.kind || f.week || f.stage || f.topic || f.set);
  // its weeks, newest first; a paper with no week last
  const weeks = [...new Set(groups.rows.map((a) => a.week ?? ""))].sort((a, b) => (a && b ? b.localeCompare(a) : a ? -1 : 1));
  const opensWeek = (w: string) => chosen || w === weeks[0] || groups.rows.some((a) => (a.week ?? "") === w && assessmentKey(a) === opened);

  // the stages that hold something, or the one chosen: a stage with nothing in it is not offered
  const stagesHere = STAGES.filter((s) => stages[s] || f.stage === s);
  // only a scan that needs a person here stays on this page; the rest are Past scans
  const needsYou = scans.filter((s) => s.status === "running" || s.noCode.length > 0 || s.lines.length > 0);

  return (
    <>
      <PageHeader stage="Assessments" title="Assessments" sub="Put papers in, make an assessment, and follow each one to done." />
      <Body>
        {/* the upload box at the top (goals/s2-the-assessment-card.yaml): papers in is the day's first job */}
        <div className="mb-[18px]">
          <ReadScan from="/papers" read={q.read} why={q.why} pages={q.pages} scans={needsYou} />
        </div>
        <div className="mb-[18px] flex flex-wrap items-start gap-3">
          {/* an opened panel is part of the page, on its own line: it never lies over the papers or runs off a phone */}
          <details className="open:w-full" data-make>
            <summary className="btn cursor-pointer list-none [&::-webkit-details-marker]:hidden">Make an assessment</summary>
            <ul className="panel mt-2 grid gap-1 p-2 md:w-fit md:min-w-[14rem]">
              {STARTS.map(([title, href]) => (
                <li key={title}>
                  <Link href={href} className="block px-3 py-2 text-basalt no-underline hover:bg-basalt/5">
                    {title}
                  </Link>
                </li>
              ))}
            </ul>
          </details>
          <details data-filters className="open:w-full">
            <summary className={`btn secondary cursor-pointer list-none [&::-webkit-details-marker]:hidden ${chosen ? "on" : ""}`}>Filter</summary>
            <form action="/papers" className="panel mt-2 grid gap-3 p-4 sm:grid-cols-2 md:w-[min(100%,36rem)]">
              <Select name="stage" label="Stage" value={f.stage} all="Every stage" options={stagesHere.map((s) => [s, STAGE_WORDS[s][0].toUpperCase() + STAGE_WORDS[s].slice(1)])} />
              <Select name="topic" label="Topic" value={f.topic} all="Every topic" options={taught.map((t) => [t.code, t.name])} />
              <Select name="class" label="Class" value={f.class} all="Every class" options={options.classes.map((c) => [c, c])} />
              <Select name="child" label="Child" value={f.child} all="Every child" options={options.children.map((c) => [c.id, c.label])} />
              <Select name="kind" label="Kind" value={f.kind} all="Any kind" options={Object.entries(KIND_WORDS)} />
              <Select name="week" label="Week" value={f.week} all="Every week" options={options.weeks.map((w) => [w, weekWords(w)])} />
              <div className="flex items-center gap-3 sm:col-span-2">
                <button type="submit" className="btn secondary">Show</button>
                {chosen ? <Link href="/papers" className="text-[13px]">Clear</Link> : null}
              </div>
            </form>
          </details>
          {/* a number only where someone must act on it: with nothing to check there is no button */}
          {toCheck ? (
            <Link href="/capture/check" className="btn secondary md:ml-auto">
              {toCheck} {toCheck === 1 ? "answer" : "answers"} to check →
            </Link>
          ) : null}
        </div>

        <section className="grid gap-[18px]" aria-label="Papers">
          {weeks.map((w) => {
            const here = groups.rows.filter((a) => (a.week ?? "") === w);
            return (
              <details key={w || "none"} data-week={w} open={opensWeek(w)} className="panel group">
                <summary className="flex cursor-pointer list-none flex-wrap items-baseline gap-x-2 px-[18px] py-3 text-[13.5px] [&::-webkit-details-marker]:hidden">
                  <span aria-hidden="true" className="inline-block w-3 text-basalt/50 transition-transform group-open:rotate-90">
                    ▸
                  </span>
                  <span className="font-semibold text-basalt">{w ? weekWords(w) : "No week"}</span>
                  <span className="text-basalt/70">· {waits(here).join(" · ")}</span>
                </summary>
                <div className="overflow-x-auto px-[18px] pb-3">
                  <AssessmentsTable
                    label={w ? `${weekWords(w)}: its assessments` : "Papers with no week"}
                    rows={here}
                    copies={copies}
                    href={(a, open) => query(f, { open: open ? "none" : assessmentKey(a) })}
                  />
                </div>
              </details>
            );
          })}
          {groups.rows.length === 0 ? <p className="note">Nothing matches these filters.</p> : null}
          {groups.more ? <p className="note">The newest 300 assessments are shown; narrow the filters to see the rest.</p> : null}
        </section>

        {/* what is over and done, behind a link each (goals/s2b-assessments-declutter.yaml) */}
        <nav aria-label="More" className="mt-6 flex flex-wrap gap-x-5 gap-y-1 text-[13px]">
          <Link href="/capture#past-scans">Past scans</Link>
          <Link href="/capture#reader">How the reader is doing</Link>
        </nav>
      </Body>
    </>
  );
}

/** A week's line: how many assessments, and only what waits in them, or that nothing does. Papers to approve and to sign
 *  off are counted as papers, the answers to check as answers — each said once, as the rows say them. */
function waits(rows: AssessmentRow[]): string[] {
  const n = rows.length;
  const sum = (f: (a: AssessmentRow) => number) => rows.reduce((k, a) => k + f(a), 0);
  const said = [
    [sum((a) => a.by.made), "to approve"],
    [sum((a) => a.waiting), "answers to check"],
    [sum((a) => a.by.checked), "to sign off"],
  ]
    .filter(([k]) => k)
    .map(([k, words]) => `${k} ${k === 1 && words === "answers to check" ? "answer to check" : words}`);
  return [`${n} assessment${n === 1 ? "" : "s"}`, ...(said.length ? said : ["nothing waiting"])];
}
