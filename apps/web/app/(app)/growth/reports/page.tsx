import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { workScope } from "@/lib/reach";
import { deadline } from "@/lib/deadline";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { reportsWaiting, reportWords } from "@/lib/queries-reports";
import { dateWords } from "@/lib/week";

// Parent reports (goals/ui4b1-child-by-topic.yaml): every child whose report waits on a person, in one list — out of
// date first, then written and waiting to be approved, then not yet written — each name opening the report, where it
// is written, read and approved.
// A class chosen at the top keeps its children alone (goals/ui6b-no-long-lists.yaml): every child of the school waiting
// at once was one long table.
export default async function ReportsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  const [every, q, g] = await Promise.all([deadline(reportsWaiting(me.email, await workScope(me))), searchParams, deadline(grades())]);
  const sections = [...new Map(every.map((r) => [r.section, r])).values()];
  const chosen = sections.some((r) => r.section === q.class) ? q.class : undefined;
  const rows = chosen ? every.filter((r) => r.section === chosen) : every;
  const n = (short: string) => rows.filter((r) => reportWords(r.report).short === short).length;
  return (
    <>
      <PageHeader
        stage="Children · parent reports"
        title="Parent reports"
        sub="Every child whose parent report is not up to date: out of date first, then written and waiting for approval, then not written yet though answers of theirs are signed off. A name opens the report."
      />
      <Body>
        <Link href="/growth" className="chip mb-[18px] inline-block">
          ← Children
        </Link>
        {sections.length ? (
          <nav aria-label="Class" className="mb-3 flex flex-wrap gap-2">
            <Link href="/growth/reports" className={`chip ${!chosen ? "on" : ""}`} aria-current={!chosen ? "page" : undefined}>
              Every class <span className="fact ml-1 opacity-70">{every.length}</span>
            </Link>
            {sections.map((r) => (
              <Link
                key={r.section}
                href={`/growth/reports?class=${encodeURIComponent(r.section)}`}
                className={`chip ${chosen === r.section ? "on" : ""}`}
                aria-current={chosen === r.section ? "page" : undefined}
              >
                {classWords(g, r.band, r.section)} <span className="fact ml-1 opacity-70">{every.filter((x) => x.section === r.section).length}</span>
              </Link>
            ))}
          </nav>
        ) : null}
        {rows.length === 0 ? (
          <Notice tone="neem">Every child&rsquo;s report is written, approved and up to date.</Notice>
        ) : (
          <Panel
            label="Parent reports not up to date"
            title="Not up to date"
            aside={`${n("out of date")} out of date · ${n("to approve")} to approve · ${n("to write")} to write`}
          >
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Parent reports not up to date">
                <thead>
                  <tr>
                    <th>Child</th>
                    <th>Class</th>
                    <th className="num">Roll</th>
                    <th>Report</th>
                    <th className="num">Written</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const { short, tone } = reportWords(r.report);
                    return (
                      <tr key={r.child_id}>
                        <td>
                          <Link href={`/growth/${r.child_id}/parent`}>{r.first_name}</Link>
                        </td>
                        <td>{classWords(g, r.band, r.section)}</td>
                        <td className="num fact">{r.roll_no}</td>
                        <td>
                          <Pill tone={tone}>{short}</Pill>
                        </td>
                        <td className="num fact">{r.report.note ? dateWords(r.report.note.written) : <span className="text-basalt/35">—</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        )}
      </Body>
    </>
  );
}
