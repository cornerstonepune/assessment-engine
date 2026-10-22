import Link from "@/components/link";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { STAGE_TONE } from "../papers/copies-table";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { across, stageOrder } from "@/lib/queries-across";
import { STAGE_WORDS } from "@/lib/queries-papers";
import { dateWords, weekWords } from "@/lib/week";

// Across every class (goals/s7-across-classes.yaml): the coordinator's page, as the scope Nimish locked on 2026-10-22
// names it — "each class and subject's stage, overdue checks, papers missing over 3 days, children struggling in two
// or more subjects". Every member of staff opens it (goals/ux9c-one-role.yaml); every class is on it, whatever is chosen
// elsewhere, since it is the page across them.
export default async function AcrossPage() {
  const me = await requireStaff();
  const [a, g] = await deadline(Promise.all([across(me.email), grades()]));
  const cls = (band: string, section: string) => classWords(g, band, section);
  return (
    <>
      <PageHeader
        stage="Children · across every class"
        title="Across every class"
        sub="Where each class's newest assessment stands in each subject, the answers waiting too long for a person, the papers not back, and the children who need help in two or more subjects."
      />
      <Body>
        <div className="grid min-w-0 gap-[18px]">
          <Panel title="Each class and subject" label="Each class and subject" aside="its newest assessment">
            {a.stages.length ? (
              <div className="min-w-0 overflow-x-auto">
                <table className="grid" aria-label="Each class and subject">
                  <thead>
                    <tr>
                      <th>Class</th>
                      <th>Subject</th>
                      <th>Newest assessment</th>
                      <th>Where its papers stand</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.stages.map((s) => (
                      <tr key={`${s.section}|${s.subject}`} data-class={s.section}>
                        <td className="whitespace-nowrap">
                          <Link href={`/growth/class/${encodeURIComponent(s.section)}`}>{cls(s.band, s.section)}</Link>
                        </td>
                        <td>{s.subject}</td>
                        <td>
                          {s.title}
                          <span className="block text-[11.5px] text-basalt/55">{weekWords(s.week)}</span>
                        </td>
                        <td>
                          <span className="flex flex-wrap gap-1">
                            {stageOrder.filter((st) => s.by[st]).map((st) => (
                              <Pill key={st} tone={STAGE_TONE[st]}>
                                {s.by[st]} {STAGE_WORDS[st]}
                              </Pill>
                            ))}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="note">No class has an assessment yet.</p>
            )}
          </Panel>

          <Panel title="Checks overdue" label="Checks overdue" aside={`waiting over ${a.hours} hours`}>
            {a.overdue.length ? (
              <ul className="grid gap-2 text-[14px]">
                {a.overdue.map((o) => (
                  <li key={o.section} data-class={o.section}>
                    <strong>{cls(o.band, o.section)}</strong>: {o.answers} {o.answers === 1 ? "answer" : "answers"} on {o.papers}{" "}
                    {o.papers === 1 ? "paper" : "papers"} waiting for a person, the oldest read {dateWords(o.oldest)}.{" "}
                    <Link href="/capture/check">Check them →</Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="note">No answer has waited for a person over {a.hours} hours.</p>
            )}
          </Panel>

          <Panel title="Papers not back" label="Papers not back" aside={`given over ${a.days} days ago`}>
            {a.missing.length ? (
              <div className="min-w-0 overflow-x-auto">
                <table className="grid" aria-label="Papers not back">
                  <thead>
                    <tr>
                      <th>Class</th>
                      <th>Roll</th>
                      <th>Paper</th>
                      <th>Given</th>
                      <th className="num">Days</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.missing.map((m) => (
                      <tr key={m.qr} data-class={m.section}>
                        <td className="whitespace-nowrap">{cls(m.band, m.section)}</td>
                        <td className="fact">{m.roll_no ?? "—"}</td>
                        <td>
                          {m.title}
                          <span className="block text-[11.5px] text-basalt/55">
                            code <Link href={`/worksheets/${m.qr}`}>{m.qr}</Link>
                          </span>
                        </td>
                        <td className="whitespace-nowrap">{dateWords(m.since)}</td>
                        <td className="num">{m.days}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="note">Every paper given over {a.days} days ago is back.</p>
            )}
          </Panel>

          <Panel title="Needing help in two or more subjects" label="Needing help in two or more subjects">
            {a.struggling.length ? (
              <ul className="grid gap-2 text-[14px]">
                {a.struggling.map((c) => (
                  <li key={c.child_id}>
                    <Link href={`/growth/${c.child_id}`}>{c.name}</Link> · {cls(c.band, c.section)} · Roll {c.roll_no}: needs help in {c.subjects.join(" and ")}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="note">
                No child needs help in two or more subjects.
                {a.subjects < 2 ? ` Only ${a.subjects === 1 ? "one subject has" : "no subject has"} children's results so far.` : ""}
              </p>
            )}
          </Panel>
        </div>
      </Body>
    </>
  );
}
