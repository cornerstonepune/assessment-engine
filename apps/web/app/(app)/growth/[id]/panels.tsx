// What a child's page holds beside the graph (goals/u2-children.yaml): the mistakes that repeat, and every paper
// made for or read from the child — its purpose, who approved it, what was read.
import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import { PURPOSE, type ChildSheet, type Repeated } from "@/lib/queries-children";
import type { Paper } from "@/lib/queries";
import { fmtDate } from "./graph";

/** `opens`: the steps whose answers the graph can open (a skill and rung with answers from a read paper). */
export function RepeatedMistakes({ rows, opens }: { rows: Repeated[]; opens: Set<string> }) {
  return (
    <Panel label="Repeated mistakes" title="Repeated mistakes" aside="the same mistake on one step, twice or more">
        {rows.length === 0 ? (
          <p className="note">No mistake has come back twice on the checked papers.</p>
        ) : (
          <ul className="grid gap-3">
            {rows.map((m) => (
              <li key={`${m.code}|${m.skill_code}|${m.rung_code}`} className="border-l-4 border-l-terracotta pl-3 text-[13.5px]">
                <div className="text-basalt">{m.name}</div>
                <div className="mt-1 text-[12.5px] text-basalt/62">
                  {m.skill_name} · {m.descriptor} · {m.times} times
                  {opens.has(`${m.rung_code}|${m.skill_code}`) ? (
                    <a href={`#ans-${m.rung_code}-${m.skill_code}`} className="ml-2">
                      the answers
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
    </Panel>
  );
}

export function TheirPapers({
  sheets,
  read,
  failed,
  staff,
}: {
  sheets: ChildSheet[];
  read: Paper[];
  failed: number;
  staff: Record<string, string>;
}) {
  return (
    <Panel label="Their papers" title="Their papers" aside={`${sheets.length}`}>
        {sheets.length === 0 ? (
          <p className="note">No paper has been made for this child or read from them yet.</p>
        ) : (
          <ul className="grid gap-3">
            {sheets.map((s) => {
              const narrative = read.find((p) => p.sheet === s.id)?.narrative;
              return (
                <li key={s.id} className="text-[13px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <Pill tone="monsoon">{s.kind ? (PURPOSE[s.kind] ?? s.kind) : "paper done in class"}</Pill>
                    <span className="fact">{s.date ? fmtDate(s.date) : s.week}</span>
                  </div>
                  <Link href={s.n_results ? `/capture/${s.id}` : `/worksheets/${s.qr_code}`} className="mt-1 block leading-snug">
                    {s.title ?? `Paper ${s.qr_code}`}
                  </Link>
                  <div className="text-[12px] text-basalt/62">
                    {s.title ? <span className="fact">{s.qr_code} · </span> : null}
                    {s.approved_by
                      ? `approved by ${staff[s.approved_by] ?? s.approved_by}${s.approved_at ? ` on ${fmtDate(s.approved_at)}` : ""}`
                      : s.print_status === "new"
                        ? "waiting for a teacher to approve"
                        : "done before papers were approved here"}
                    {s.n_results ? ` · ${s.n_confirmed} of ${s.n_results} answers checked` : ""}
                  </div>
                  {narrative ? <p className="mt-1 text-[12.5px] italic text-basalt/75">{narrative}</p> : null}
                </li>
              );
            })}
          </ul>
        )}
        {failed > 0 ? <p className="note mt-3">{failed} read{failed === 1 ? "" : "s"} failed and count for nothing.</p> : null}
        <p className="note mt-3">The scans stay on the school&rsquo;s drive; what the child wrote is shown under each step.</p>
    </Panel>
  );
}
