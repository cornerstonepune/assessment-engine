import Link from "@/components/link";
import { Body, PageHeader, Panel, Pill, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { papersToApprove } from "@/lib/queries-read";
import { deadline } from "@/lib/deadline";

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

export default async function CapturePage() {
  const me = await requireStaff();
  const papers = await deadline(papersToApprove(me.email));
  const waiting = papers.filter((p) => p.n_candidate > 0);
  const done = papers.filter((p) => p.n_candidate === 0 && p.n_results > 0);
  const broken = papers.filter((p) => p.n_results === 0);
  const answers = papers.reduce((n, p) => n + p.n_results, 0);
  const flagged = papers.reduce((n, p) => n + p.n_flagged, 0);

  return (
    <>
      <PageHeader
        stage="Stage 3 · Read"
        title="Capture & Mark"
        sub="Every paper the engine has read, and what it wants you to look at. Nothing reaches a child's ladder until you have said it is right."
      />
      <Body>
        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-4">
          <Tile tone="terracotta" n={waiting.length} words={`paper${waiting.length === 1 ? "" : "s"} waiting for you`} />
          <Tile tone="bamboo" n={flagged} words="answers the reader was unsure of" />
          <Tile tone="neem" n={done.length} words="papers you have signed off" />
          <Tile tone="monsoon" n={answers} words="answers read in all" />
        </div>

        <div className="grid min-w-0 gap-[18px]">
          <Panel title="Waiting for you" aside={`${waiting.length} paper${waiting.length === 1 ? "" : "s"}`}>
            {waiting.length === 0 ? (
              <p className="note">Nothing is waiting. Every paper read so far has been signed off.</p>
            ) : (
              <PaperTable rows={waiting} />
            )}
          </Panel>

          {done.length > 0 ? (
            <Panel title="Signed off" aside={`${done.length}`}>
              <PaperTable rows={done} />
            </Panel>
          ) : null}

          {broken.length > 0 ? (
            <Panel title="Read, but nothing came back" aside={`${broken.length}`}>
              <p className="note mb-3">
                These papers were opened and produced no answers at all. A paper entered with the wrong questions, or a
                read that failed part way — either way nothing here counts for anything yet.
              </p>
              <PaperTable rows={broken} />
            </Panel>
          ) : null}
        </div>
      </Body>
    </>
  );
}

function PaperTable({ rows }: { rows: Awaited<ReturnType<typeof papersToApprove>> }) {
  return (
    <div className="min-w-0 overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            <th>Child</th>
            <th>Paper</th>
            <th>Sat</th>
            <th className="text-right">Answers</th>
            <th className="text-right">Not signed yet</th>
            <th>State</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td>
                {p.first_name}
                <div className="text-[12px] text-basalt/55">{p.section}</div>
              </td>
              <td className="max-w-[280px] text-[13px]">
                <Link href={`/capture/${p.id}`}>{p.title ?? p.paper}</Link>
              </td>
              <td className="fact whitespace-nowrap">{fmtDate(p.date)}</td>
              <td className="num">{p.n_results}</td>
              <td className="num">{p.n_candidate || "—"}</td>
              <td className="whitespace-nowrap">
                {p.n_results === 0 ? (
                  <Pill tone="terracotta">nothing read</Pill>
                ) : p.n_candidate === 0 ? (
                  <Pill tone="neem">signed off</Pill>
                ) : p.n_flagged > 0 ? (
                  <Pill tone="bamboo">{p.n_flagged} need your eyes</Pill>
                ) : (
                  <Pill tone="monsoon">read, not confirmed</Pill>
                )}
                {p.n_corrected > 0 ? (
                  <span className="ml-2 text-[12px] text-basalt/55">{p.n_corrected} corrected</span>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
