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
  type PaperListRow,
  type Stage,
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

// What waits in a week, in words: only the stages that wait on a person, and only those that are there.
const WAITS: [Stage, string][] = [["made", "to approve"], ["scanned", "to check"], ["checked", "to sign off"]];

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
  const [groups, { stages, options }, queue] = await deadline(
    Promise.all([assessmentList(f, scopeOf(me)), paperFilters(f, me.email, scopeOf(me)), checkQueue(scopeOf(me))]),
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
  const all = STAGES.reduce((n, s) => n + stages[s], 0);
  const folded = !!(f.class || f.child || f.kind || f.week);
  const chosen = folded || !!(f.stage || f.topic || f.set);
  // its weeks, newest first; a paper with no week last
  const weeks = [...new Set(groups.rows.map((a) => a.week ?? ""))].sort((a, b) => (a && b ? b.localeCompare(a) : a ? -1 : 1));
  const opensWeek = (w: string) => chosen || w === weeks[0] || groups.rows.some((a) => (a.week ?? "") === w && assessmentKey(a) === opened);

  return (
    <>
      <PageHeader
        stage="Assessments"
        title="Assessments"
        sub="Make an assessment, then follow every one from approval to done, week by week. An assessment opens to its copies; a copy opens to print it, or to check its answers once it is read."
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

        <nav aria-label="Topic" className="mb-3 flex flex-wrap gap-2">
          <Link href={query(f, { topic: undefined })} className={`chip ${!f.topic ? "on" : ""}`} aria-current={!f.topic ? "page" : undefined}>
            All topics
          </Link>
          {taught.map((t) => (
            <Link
              key={t.code}
              href={query(f, { topic: t.code })}
              className={`chip ${f.topic === t.code ? "on" : ""}`}
              aria-current={f.topic === t.code ? "page" : undefined}
            >
              {t.name}
            </Link>
          ))}
        </nav>

        <nav aria-label="Papers by stage" className="mb-3 flex flex-wrap gap-2">
          <Link href={query(f, { stage: undefined })} className={`chip ${!f.stage ? "on" : ""}`}
            aria-current={!f.stage ? "page" : undefined}>
            Every stage <span className="fact ml-1 opacity-70">{all}</span>
          </Link>
          {STAGES.map((s) => (
            <Link key={s} href={query(f, { stage: s })} className={`chip ${f.stage === s ? "on" : ""}`}
              aria-current={f.stage === s ? "page" : undefined}>
              {STAGE_WORDS[s][0].toUpperCase() + STAGE_WORDS[s].slice(1)} <span className="fact ml-1 opacity-70">{stages[s]}</span>
            </Link>
          ))}
        </nav>

        <details data-filters open={folded} className="mb-[18px]">
          <summary className="cursor-pointer text-[13px] text-basalt/75">Class, child, kind and week</summary>
          <form action="/papers" className="panel mt-2 flex flex-wrap items-end gap-3 p-4">
            {f.stage ? <input type="hidden" name="stage" value={f.stage} /> : null}
            {f.topic ? <input type="hidden" name="topic" value={f.topic} /> : null}
            <Select name="class" label="Class" value={f.class} all="Every class" options={options.classes.map((c) => [c, c])} />
            <Select name="child" label="Child" value={f.child} all="Every child" options={options.children.map((c) => [c.id, c.label])} />
            <Select name="kind" label="Kind" value={f.kind} all="Any kind" options={Object.entries(KIND_WORDS)} />
            <Select name="week" label="Week" value={f.week} all="Every week" options={options.weeks.map((w) => [w, weekWords(w)])} />
            <button type="submit" className="btn">Show</button>
            {chosen ? <Link href="/papers" className="text-[13px]">Clear</Link> : null}
          </form>
        </details>

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

        <div className="mt-[18px]">
          <ReadScan from="/papers" read={q.read} why={q.why} pages={q.pages} />
        </div>
      </Body>
    </>
  );
}

/** A week's line: how many assessments, and only what waits in them, or that nothing does. */
function waits(rows: AssessmentRow[]): string[] {
  const n = rows.length;
  const said = WAITS.map(([s, words]) => [rows.reduce((k, a) => k + a.by[s], 0), words] as const)
    .filter(([k]) => k)
    .map(([k, words]) => `${k} ${words}`);
  return [`${n} assessment${n === 1 ? "" : "s"}`, ...(said.length ? said : ["nothing waiting"])];
}
