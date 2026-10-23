import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip } from "@/components/status-chip";
import type { QueueLine } from "@/lib/queries-read";
import type { Column } from "@/lib/ux-rules";

export type QueueRow = QueueLine & { at: number };

// What is left to check, as one table (goals/uxn7-check-answers.yaml): where each answer sits in the queue, whose paper
// it is by class and roll number, which question, and why it is here; a click opens that answer.
export function QueueTable({ rows, page, pageHref }: { rows: QueueRow[]; page: number; pageHref: (n: number) => string }) {
  const columns: Column<QueueRow>[] = [
    { key: "at", label: "#", num: true, width: "4rem", value: (r) => r.at },
    { key: "class", label: "Class", width: "9rem", value: (r) => r.section },
    { key: "roll", label: "Roll", num: true, width: "4.5rem", value: (r) => r.roll_no },
    { key: "paper", label: "Paper", value: (r) => r.paper },
    { key: "question", label: "Question", width: "6.5rem", value: (r) => r.slot },
    { key: "state", label: "Status", status: true, width: "10rem", value: (r) => (r.spot ? "spot" : "toCheck"), cell: (r) => <StatusChip state={r.spot ? "spot" : "toCheck"} /> },
    { key: "open", label: "", width: "6rem", keep: true, value: (r) => r.id, cell: (r) => <Link href={`/capture/check?id=${r.id}`}>Check this</Link> },
  ];
  return <DataTable label="Left to check" columns={columns} rows={rows} rowKey={(r) => r.id} more={{ page, href: pageHref }} />;
}
