import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { classWords } from "@/lib/needs-you";
import { reportsWaiting, reportWords } from "@/lib/queries-reports";

// Parent reports (goals/ui4b1-child-by-topic.yaml): every child whose report waits on a person, in one list — out of
// date first, then written and waiting to be approved, then not yet written — each name opening the report, where it
// is written, read and approved.
export default async function ReportsPage() {
  const me = await requireStaff();
  const rows = await deadline(reportsWaiting(me.email));
  const n = (short: string) => rows.filter((r) => reportWords(r.report).short === short).length;
  return (
    <>
      <PageHeader
        stage="Children · parent reports"
        title="Parent reports"
        sub="Every child whose parent report waits on a person: out of date first, then written and waiting for approval, then not yet written though answers of theirs are signed off. A name opens the report."
      />
      <Body>
        <Link href="/growth" className="chip mb-[18px] inline-block">
          ← Children
        </Link>
        {rows.length === 0 ? (
          <Notice tone="neem">Every child&rsquo;s report is written, approved and up to date.</Notice>
        ) : (
          <Panel
            label="Parent reports waiting"
            title="Waiting on a person"
            aside={`${n("out of date")} out of date · ${n("to approve")} to approve · ${n("to write")} to write`}
          >
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Parent reports waiting on a person">
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
                        <td>{classWords(r.band, r.section)}</td>
                        <td className="num fact">{r.roll_no}</td>
                        <td>
                          <Pill tone={tone}>{short}</Pill>
                        </td>
                        <td className="num fact">{r.report.note?.written ?? <span className="text-basalt/35">—</span>}</td>
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
