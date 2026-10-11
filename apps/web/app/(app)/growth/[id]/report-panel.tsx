import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import { reportWords, type ReportState } from "@/lib/queries-reports";

// The last part of a child's page (goals/ui4b1-child-by-topic.yaml): their parent report, its state in words, one
// click from where it is written, read and approved — and no link at all while there is nothing to write it from.
export function ParentReportPanel({ childId, report, approver }: { childId: string; report: ReportState; approver: string | null }) {
  const { words, tone } = reportWords(report);
  const { note, signed } = report;
  return (
    <Panel id="parent-report" label="Parent report" title="Parent report">
      <p className="mb-3 flex flex-wrap items-center gap-2 text-[13.5px]">
        <Pill tone={tone}>{words}</Pill>
        {note ? <span className="text-basalt/62">written {note.written}{approver ? `, approved by ${approver}` : ""}</span> : null}
      </p>
      {note || signed ? (
        <Link href={`/growth/${childId}/parent`} className="text-[13px]">
          {note ? "Open the report →" : "Write it →"}
        </Link>
      ) : null}
    </Panel>
  );
}
