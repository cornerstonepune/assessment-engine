import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { papersToApprove, readerReport } from "@/lib/queries-read";
import { lastScans } from "@/lib/queries-scans";
import { deadline } from "@/lib/deadline";
import { ReadScan } from "./read-scan";
import { ReaderPanel, standing } from "./parts";
import { ByChild, ByClass, ByWorksheet, ChildPapers, NothingRead, WorksheetPapers } from "./views";

type Props = { searchParams: Promise<Record<string, string | undefined>> };
const VIEWS = [
  ["child", "By child"],
  ["class", "By class"],
  ["worksheet", "By worksheet"],
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

        <nav aria-label="Read marking" className="mb-[18px] flex flex-wrap gap-2">
          {VIEWS.map(([v, words]) => (
            <Link
              key={v}
              href={`/capture?by=${v}`}
              className={`chip ${by === v ? "!bg-basalt !text-chalk" : ""}`}
              aria-current={by === v ? "page" : undefined}
            >
              {words}
            </Link>
          ))}
        </nav>

        <div className="grid min-w-0 gap-[18px]">
          {by === "class" ? <ByClass papers={papers} /> : null}
          {by === "child" ? <ByChild papers={papers} open={(section) => !!scope.classes || section === q.class} /> : null}
          {by === "worksheet" ? <ByWorksheet papers={papers} /> : null}
          <ReaderPanel r={reader} />
          <NothingRead papers={papers} />
        </div>
    </PageShell>
  );
}
