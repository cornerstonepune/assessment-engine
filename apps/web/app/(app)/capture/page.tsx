import Link from "@/components/link";
import { Body, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { checkQueue, papersToApprove, readerReport } from "@/lib/queries-read";
import { deadline } from "@/lib/deadline";
import { readScan } from "./actions";
import { Count, ReaderPanel, standing } from "./parts";
import { ByChild, ByClass, ByWorksheet, ChildPapers, NothingRead, WorksheetPapers } from "./views";

type Props = { searchParams: Promise<Record<string, string | undefined>> };
const VIEWS = [
  ["class", "By class"],
  ["child", "By child"],
  ["worksheet", "By worksheet"],
] as const;

// Marking (goals/u3-marking.yaml): Capture & Mark and Check answers as one area. Papers in, and every answer on
// them settled by the engine, checked by a person or still waiting — by class, child or worksheet — the queue of
// answers to check one click away, and how the reader is doing. Where each answer stands is the engine's
// (answer_standing); this page only counts it.
// A scan read from its Drive link (N8): the engine fetches the file and reads it after this page has answered, so
// the notice says it has started; the papers appear above as they are read. What the engine would not take, in its
// own words.
function ReadScan({ read, why, pages }: { read?: string; why?: string; pages?: string }) {
  const said = {
    started: `Reading ${Number(pages) || ""} pages. The papers appear here as they are read — a minute or two.`,
    refused: `The engine would not take that: ${why ?? ""}`,
    "not-a-link": "Paste the link to the scan on Google Drive (drive.google.com/…).",
    engine: "The engine is not answering; nothing was read.",
  }[read ?? ""];
  return (
    <Panel title="Read a scan" label="Read a scan" id="read-scan">
      <form action={readScan} className="flex flex-wrap items-center gap-2">
        <input
          type="url"
          name="url"
          required
          placeholder="https://drive.google.com/file/d/…/view"
          aria-label="Link to the scan on Google Drive"
          className="min-w-0 flex-1 rounded border border-line bg-chalk px-3 py-2 text-[14px]"
        />
        <button type="submit" className="btn">
          Read it
        </button>
      </form>
      <p className="mt-2 text-[13px] text-ink-soft">
        {said ?? "Every page is sorted by the code printed on it and read in its boxes; every answer waits here for a person. A copy printed without a child's code is listed, not guessed."}
      </p>
    </Panel>
  );
}

export default async function MarkingPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const [papers, reader, queue] = await deadline(Promise.all([papersToApprove(me.email), readerReport(), checkQueue()]));
  if (q.child) return <ChildPapers papers={papers} id={q.child} />;
  if (q.worksheet) return <WorksheetPapers papers={papers} worksheet={q.worksheet} />;

  const by = VIEWS.some(([v]) => v === q.by) ? q.by : "child";
  const all = standing(papers);
  // the queue's own count, as Check answers shows it: spot-checks are the engine's, not waiting on anyone
  const toCheck = queue.filter((e) => !e.spot).length;

  return (
    <>
      <PageHeader
        stage="Marking"
        title="Marking"
        sub="Papers in, and where every answer on them stands: settled by the engine, checked by a person, or still waiting. Check what waits one answer at a time; sign a child's papers off to build their graph."
      />
      <Body>
        <section aria-label="Answers to check" className="panel mb-[18px] flex flex-wrap items-center gap-4 border-l-4 border-l-bamboo p-4">
          {toCheck ? (
            <>
              <span className="font-heading text-[26px] leading-none" data-testid="count">
                {toCheck}
              </span>
              <span className="text-[14px]">answers the engine was not sure of, one at a time with the child&rsquo;s own writing</span>
              <Link href="/capture/check" className="btn md:ml-auto">
                Check them →
              </Link>
            </>
          ) : (
            <span className="text-[14px]">Nothing waiting: every answer read is settled, by the engine or by a person.</span>
          )}
        </section>

        <section aria-label="Where every answer stands" className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-5">
          <Count id="papers" n={all.papers} words="papers in" tone="monsoon" />
          <Count id="engine" n={all.engine} words="answers settled by the engine" tone="neem" />
          <Count id="person" n={all.person} words="answers checked by a person" tone="neem" />
          <Count id="waiting" n={all.waiting} words="answers still waiting" tone="bamboo" />
          <Count id="to-sign" n={all.toSign} words="papers to sign off" tone="terracotta" />
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
          {by === "child" ? <ByChild papers={papers} only={q.class} /> : null}
          {by === "worksheet" ? <ByWorksheet papers={papers} /> : null}
          <ReadScan read={q.read} why={q.why} pages={q.pages} />
          <ReaderPanel r={reader} />
          <NothingRead papers={papers} />
        </div>
      </Body>
    </>
  );
}
