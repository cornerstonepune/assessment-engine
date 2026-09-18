import Link from "next/link";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { childrenOnRoll } from "@/lib/queries";

export default async function GrowthPage() {
  const me = await requireStaff();
  const rows = await childrenOnRoll(me.email);
  const sections = [...new Set(rows.map((r) => r.section))];
  const withEvidence = rows.filter((r) => r.n_events > 0).length;
  const waiting = rows.reduce((a, r) => a + r.n_pending, 0);

  return (
    <>
      <PageHeader
        stage="Stage 4 · Understand"
        title="Child Growth"
        sub="One child: what they can do on each rung, in six states, and what the next paper should be."
      />
      <Body>
        <div className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
          {sections.map((section) => (
            <Panel
              key={section}
              title={section}
              aside={`${rows.filter((r) => r.section === section).length} on roll`}
            >
              <div className="overflow-x-auto">
              <table className="grid">
                <thead>
                  <tr>
                    <th>Roll</th>
                    <th>Child</th>
                    <th>Band</th>
                    <th className="text-right">Papers read</th>
                    <th className="text-right">Confirmed answers</th>
                    <th className="text-right">Waiting for a person</th>
                  </tr>
                </thead>
                <tbody>
                  {rows
                    .filter((r) => r.section === section)
                    .map((r) => (
                      <tr key={r.id}>
                        <td className="fact">{r.roll_no}</td>
                        <td>
                          <Link href={`/growth/${r.id}`} className="underline decoration-basalt/30 underline-offset-4">
                            {r.first_name}
                          </Link>
                        </td>
                        <td className="fact">{r.band}</td>
                        <td className="num">{r.n_papers}</td>
                        <td className="num">{r.n_events}</td>
                        <td className="num">
                          {r.n_pending > 0 ? <Pill tone="bamboo">{r.n_pending}</Pill> : <span className="text-basalt/40">—</span>}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              </div>
            </Panel>
          ))}
          <p className="note">
            {withEvidence} of {rows.length} children have confirmed evidence · {waiting} answers waiting for a person. Papers
            are read with <code>engine legacy import</code>; a person confirms them here.
          </p>
        </div>
      </Body>
    </>
  );
}
