import { after } from "next/server";
import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { PageShell } from "@/components/page-shell";
import { ReportForm } from "@/components/report-form";
import { StatusChip, type State } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { limits, myReports, reporterMark, sendWaiting, type MyReport } from "@/lib/feedback";
import { KINDS, type Seen } from "@/lib/feedback-words";
import type { Column } from "@/lib/ux-rules";
import { dateWords } from "@/lib/week";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Report a problem or suggest something (goals/feed_report_from_the_tool.yaml). Nimish, 27 Oct 2026: "one can raise a
// feature request or file a bug, and that directly reaches you as an issue, and then we decide to work on it." Reached
// from the top bar of every page, which says where the person came from (`from`). Opening the page also tries again the
// notes that have not reached GitHub yet, after the page has answered.
const CHIP: Record<Seen, [State, string]> = {
  received: ["notYet", "received"],
  takenUp: ["waiting", "taken up"],
  done: ["done", "done"],
};

const columns: Column<MyReport>[] = [
  { key: "title", label: "Your words", value: (r) => r.title },
  { key: "kind", label: "Kind", value: (r) => KINDS[r.kind].words, width: "14rem" },
  { key: "on", label: "Sent on", value: (r) => dateWords(r.created_at.toISOString()), width: "8rem" },
  { key: "seen", label: "Status", status: true, value: (r) => r.seen, cell: (r) => <StatusChip state={CHIP[r.seen][0]} words={CHIP[r.seen][1]} />, width: "9rem" },
];

export default async function ReportPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const [mine, { maxChars }] = await deadline(Promise.all([myReports(reporterMark(me.email)), limits()]));
  after(() => sendWaiting());
  const page = Number(q.page) || 1;
  return (
    <PageShell
      stage="Help"
      title="Report a problem or suggest something"
      purpose="Tell us what is broken, what you would like, or ask a question. It reaches the team, who decide what is built."
      action={<span className="note">One note at a time, in your own words.</span>}
      next={{ href: "/today", label: "What needs doing" }}
    >
      <ReportForm from={q.from ?? "/"} maxChars={maxChars} />
      <section className="mt-8" aria-label="Your reports">
        <h2 className="mb-2 text-[16px]">Your reports</h2>
        {mine.length ? (
          <DataTable
            label="Your reports"
            columns={columns}
            rows={mine}
            rowKey={(r) => r.id}
            more={{ page, href: (n: number) => `/feedback?page=${n}` }}
            extras={{ attrs: (r) => ({ "data-report": r.seen }) }}
          />
        ) : (
          <p className="note">Nothing sent yet. What you send shows here, and whether it was taken up or done.</p>
        )}
        <p className="note mt-2">
          Taken up means it will be built; done means it is finished. <Link href="/today">Back to what needs doing</Link>
        </p>
      </section>
    </PageShell>
  );
}
