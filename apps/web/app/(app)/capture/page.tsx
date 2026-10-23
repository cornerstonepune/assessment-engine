import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { papersToApprove, readerReport } from "@/lib/queries-read";
import { lastScans } from "@/lib/queries-scans";
import { deadline } from "@/lib/deadline";
import { ReadScan } from "./read-scan";
import { FilterBar } from "@/components/filter-bar";
import { ReaderPanel, standing } from "./parts";
import { READER_VIEWS, type ReaderView } from "./reader-table";
import { ByChild, ByClass, ByWorksheet, ChildPapers, NothingRead, WorksheetPapers } from "./views";

type Props = { searchParams: Promise<Record<string, string | undefined>> };
const VIEWS = [
  ["class", "By class"],
  ["worksheet", "By worksheet"],
] as const;
const STATUS = [
  ["check", "Answers to check"],
  ["sign", "Papers to sign off"],
  ["signed", "Signed off"],
] as const;
const N = ({ id, n }: { id: string; n: number }) => <strong data-testid={id}>{n}</strong>;

// Marking (goals/u3-marking.yaml): Capture & Mark and Check answers as one area. Papers in, and every answer on
// them settled by the engine, checked by a person or still waiting — by class, child or worksheet — the queue of
// answers to check one click away, and how the reader is doing. Where each answer stands is the engine's
// (answer_standing); this page only counts it. What is in and what waits is one sentence; by child, each class is one
// line, open for the educator who teaches it (goals/ux5b-make-and-marking.yaml).
export default async function MarkingPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const scope = scopeOf(me);
  const [papers, reader, scans] = await deadline(Promise.all([papersToApprove(me.email, scope), readerReport(), lastScans(scope)]));
  if (q.child) return <ChildPapers papers={papers} id={q.child} />;
  if (q.worksheet) return <WorksheetPapers papers={papers} worksheet={q.worksheet} />;

  const by = VIEWS.some(([v]) => v === q.by) ? q.by : "child";
  const all = standing(papers);
  // narrowed by class and by where a paper stands (goals/uxn8-marking.yaml); the sentence above still counts every paper
  const classes = [...new Set(papers.map((p) => p.section))].sort();
  const section = (q.class && classes.includes(q.class) ? q.class : undefined) ?? (scope.classes?.length === 1 && classes.includes(scope.classes[0]) ? scope.classes[0] : undefined);
  const status = STATUS.some(([v]) => v === q.status) ? q.status : undefined;
  const shown = papers.filter(
    (p) =>
      (!section || p.section === section) &&
      (!status ||
        (status === "check" ? p.n_waiting > 0 : status === "sign" ? p.n_waiting === 0 && p.n_results > 0 && p.n_candidate > 0 : p.n_results > 0 && p.n_candidate === 0)),
  );
  const page = Math.max(1, Math.floor(Number(q.page)) || 1);
  const here = { by: by === "child" ? undefined : by, class: section, status };
  const pageHref = (n: number) => `/capture?${new URLSearchParams({ ...Object.fromEntries(Object.entries(here).filter(([, v]) => v) as [string, string][]), page: String(n) })}`;
  const readerView: ReaderView = READER_VIEWS.some(([v]) => v === q.reader) ? (q.reader as ReaderView) : "day";

  return (
    <PageShell
      stage="Upload papers"
      title="Upload papers"
      purpose="Papers in, and where every answer on them stands: settled by the engine, checked by a person, or still waiting."
      action={
        all.waiting ? (
          <Link href="/capture/check" className="btn">
            Check {all.waiting} {all.waiting === 1 ? "answer" : "answers"} →
          </Link>
        ) : (
          <Link href="/capture/check" className="btn secondary">
            Check answers
          </Link>
        )
      }
      next={{ href: "/growth", label: "Class results" }}
    >
        {/* the upload box at the top (goals/s2-the-assessment-card.yaml) */}
        <div className="mb-[18px] grid min-w-0">
          <ReadScan from="/capture" read={q.read} why={q.why} pages={q.pages} scans={scans} />
        </div>
        <section aria-label="Answers to check" className="panel mb-[18px] flex flex-wrap items-center gap-4 border-l-4 border-l-bamboo p-4">
          <p className="text-[14px]">
            <N id="papers" n={all.papers} /> {all.papers === 1 ? "paper" : "papers"} in: <N id="engine" n={all.engine} />{" "}
            {all.engine === 1 ? "answer" : "answers"} settled by the engine, <N id="person" n={all.person} /> checked by a person,{" "}
            <N id="waiting" n={all.waiting} /> waiting for you to check; <N id="to-sign" n={all.toSign} />{" "}
            {all.toSign === 1 ? "paper" : "papers"} to sign off.
          </p>
        </section>

        <FilterBar
          action="/capture"
          filters={[
            { name: "by", label: "Show", value: by === "child" ? undefined : by, all: "By child", options: VIEWS },
            { name: "class", label: "Class", value: section, all: "Every class", options: classes.map((c) => [c, c] as const) },
            { name: "status", label: "Status", value: status, all: "Any status", options: STATUS },
          ]}
        />

        <div className="grid min-w-0 gap-[18px]">
          {by === "class" ? <ByClass papers={shown} page={page} pageHref={pageHref} /> : null}
          {by === "child" ? <ByChild papers={shown} section={section} page={page} pageHref={pageHref} /> : null}
          {by === "worksheet" ? <ByWorksheet papers={shown} page={page} pageHref={pageHref} /> : null}
          <NothingRead papers={papers} />
          <details open={!!q.reader || !!q.rpage} className="panel p-0">
            <summary className="cursor-pointer px-[18px] py-3 text-[14px]">How the reader is doing, for the people who build it</summary>
            <ReaderPanel r={reader} view={readerView} page={Math.max(1, Math.floor(Number(q.rpage)) || 1)} keep={{ ...here, page: undefined }} />
          </details>
        </div>
    </PageShell>
  );
}
