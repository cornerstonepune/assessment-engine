import Link from "@/components/link";
import { Count } from "@/components/count";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { PageShell } from "@/components/page-shell";
import { Panel, Pill } from "@/components/shell";
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
    <PageShell
      stage="Children · across every class"
      title="Across every class"
      purpose="Where each class's newest assessment stands, answers waiting too long, papers not back, and children needing help in two subjects."
      action={
        <Link href="/capture/check" className="btn">
          Check answers
        </Link>
      }
      next={{ href: "/growth", label: "Children" }}
    >
      <div className="grid min-w-0 gap-[18px]">
        <Panel title="Each class and subject" label="Each class and subject" aside="its newest assessment">
          {a.stages.length ? (
            <DataTable
              label="Each class and subject"
              rows={a.stages}
              rowKey={(s) => `${s.section}|${s.subject}`}
              more={{ by: (s) => cls(s.band, s.section), href: (name: string) => `/growth/class/${encodeURIComponent(a.stages.find((s) => cls(s.band, s.section) === name)?.section ?? "")}` }}
              columns={[
                { key: "subject", label: "Subject", value: (s) => s.subject, keep: true },
                {
                  key: "title",
                  label: "Newest assessment",
                  value: (s) => s.title,
                  cell: (s) => (
                    <>
                      {s.title}
                      <span className="block text-[11.5px] text-basalt/55">{weekWords(s.week)}</span>
                    </>
                  ),
                },
                {
                  key: "stage",
                  label: "Where its papers stand",
                  value: (s) => stageOrder.filter((st) => s.by[st]).length,
                  cell: (s) => (
                    <span className="flex flex-wrap gap-1">
                      {stageOrder.filter((st) => s.by[st]).map((st) => (
                        <Pill key={st} tone={STAGE_TONE[st]}>
                          {s.by[st]} {STAGE_WORDS[st]}
                        </Pill>
                      ))}
                    </span>
                  ),
                },
              ]}
            />
          ) : (
            <EmptyState>No class has an assessment yet.</EmptyState>
          )}
        </Panel>

        <Panel title="Checks overdue" label="Checks overdue" aside={`waiting over ${a.hours} hours`}>
          {a.overdue.length ? (
            <ul className="grid gap-2 text-[14px]">
              {a.overdue.map((o) => (
                <li key={o.section} data-class={o.section}>
                  <strong>{cls(o.band, o.section)}</strong>: <Count of="overdue-answers" n={o.answers} /> {o.answers === 1 ? "answer" : "answers"} on{" "}
                  {o.papers} {o.papers === 1 ? "paper" : "papers"} waiting for a person, the oldest read {dateWords(o.oldest)}.{" "}
                  <Link href="/capture/check">Check them →</Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>No answer has waited for a person over {a.hours} hours.</EmptyState>
          )}
        </Panel>

        <Panel title="Papers not back" label="Papers not back" aside={`given over ${a.days} days ago`}>
          {a.missing.length ? (
            <DataTable
              label="Papers not back"
              rows={a.missing}
              rowKey={(m) => m.qr}
              more={{ by: (m) => cls(m.band, m.section) }}
              columns={[
                { key: "roll", label: "Roll", value: (m) => m.roll_no },
                {
                  key: "paper",
                  label: "Paper",
                  value: (m) => m.title,
                  cell: (m) => (
                    <>
                      {m.title}
                      <span className="block text-[11.5px] text-basalt/55">
                        code <Link href={`/worksheets/${m.qr}`}>{m.qr}</Link>
                      </span>
                    </>
                  ),
                },
                { key: "given", label: "Given", value: (m) => dateWords(m.since) },
                { key: "days", label: "Days", value: (m) => m.days, num: true },
              ]}
            />
          ) : (
            <EmptyState>Every paper given over {a.days} days ago is back.</EmptyState>
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
            <EmptyState>
              No child needs help in two or more subjects.
              {a.subjects < 2 ? ` Only ${a.subjects === 1 ? "one subject has" : "no subject has"} children's results so far.` : ""}
            </EmptyState>
          )}
        </Panel>
      </div>
    </PageShell>
  );
}
