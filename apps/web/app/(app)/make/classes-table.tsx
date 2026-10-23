import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import type { Column } from "@/lib/ux-rules";
import { weekWords } from "@/lib/week";

export type ClassLine = { section: string; grade: string; children: number; proposed: number; approved: number; tooFew: number };
export type PackLine = { section: string; week: string; kind: string; n: number };

export const classState = (c: ClassLine): State => (c.proposed > 0 ? "toApprove" : c.approved >= c.children ? "done" : "waiting");

// Each class's home assessments for the week, as a table (goals/uxn5-print-and-give.yaml): the same columns as every list.
export function ClassesTable({ rows, page, pageHref }: { rows: ClassLine[]; page: number; pageHref: (n: number) => string }) {
  const cols: Column<ClassLine>[] = [
    { key: "class", label: "Class", width: "9rem", value: (c) => c.section, cell: (c) => <span className="fact">{c.section}</span> },
    { key: "grade", label: "Grade", width: "8rem", value: (c) => c.grade },
    { key: "children", label: "Children", num: true, width: "6rem", value: (c) => c.children },
    { key: "proposed", label: "Proposed", num: true, width: "6rem", value: (c) => c.proposed, cell: (c) => <span data-n="proposed">{c.proposed}</span> },
    { key: "approved", label: "Approved", num: true, width: "6rem", value: (c) => c.approved, cell: (c) => <span data-n="approved">{c.approved}</span> },
    // the rest of the class, so a zero above says why (goals/ux8b-papers-named.yaml)
    { key: "few", label: "Not enough checked work yet", num: true, width: "9rem", value: (c) => c.tooFew, cell: (c) => <span data-n="too-few">{c.tooFew}</span> },
    { key: "state", label: "Status", status: true, width: "10rem", value: (c) => classState(c), cell: (c) => <StatusChip state={classState(c)} words={classState(c) === "waiting" ? "not enough work yet" : undefined} /> },
    { key: "open", label: "", width: "6rem", keep: true, value: (c) => c.section, cell: (c) => <Link href={`/make/${encodeURIComponent(c.section)}`}>Open</Link> },
  ];
  return <DataTable label="Home assessments this week" columns={cols} rows={rows} rowKey={(c) => c.section} more={{ page, href: pageHref }} />;
}

// The class papers (a practice or an assessment for a week) waiting for a person.
export function PacksTable({ rows, page, pageHref }: { rows: PackLine[]; page: number; pageHref: (n: number) => string }) {
  const cols: Column<PackLine>[] = [
    { key: "class", label: "Class", width: "9rem", value: (p) => p.section, cell: (p) => <span className="fact">{p.section}</span> },
    { key: "week", label: "Week", width: "10rem", value: (p) => weekWords(p.week) },
    { key: "kind", label: "Kind", width: "10rem", value: (p) => (p.kind === "assessment" ? "class assessment" : "class practice") },
    { key: "n", label: "Papers", num: true, width: "6rem", value: (p) => p.n },
    { key: "state", label: "Status", status: true, width: "10rem", value: () => "toApprove", cell: () => <StatusChip state="toApprove" /> },
    {
      key: "open",
      label: "",
      keep: true,
      value: (p) => p.section,
      cell: (p) => <Link href={`/papers/approve?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`}>Look over and approve</Link>,
    },
  ];
  return (
    <DataTable
      label="Class papers waiting for approval"
      columns={cols}
      rows={rows}
      rowKey={(p) => `${p.section}|${p.week}|${p.kind}`}
      more={{ page, href: pageHref }}
    />
  );
}
