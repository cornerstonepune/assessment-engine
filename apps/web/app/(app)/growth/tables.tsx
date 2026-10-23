import Link from "@/components/link";
import { DataTable, type Sort } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import type { ChildRow } from "@/lib/queries-children";
import { reportWaits, reportWords } from "@/lib/queries-reports";
import type { Column } from "@/lib/ux-rules";

// Class results as tables (goals/uxn9-class-results.yaml): the classes side by side, then the children of one class (or
// the children who need the educator, across the classes), each with a state in a chip.

export type ClassLine = { section: string; grade: string; kids: ChildRow[] };

const sum = (kids: ChildRow[], f: (c: ChildRow) => number) => kids.reduce((n, c) => n + f(c), 0);
const classState = (kids: ChildRow[]): State => (kids.some((c) => c.needs_help > 0) ? "needsHelp" : kids.some((c) => c.waiting > 0 || reportWaits(c.report)) ? "waiting" : "fine");
export const childState = (c: ChildRow): { state: State; words?: string } =>
  c.needs_help > 0 ? { state: "needsHelp" } : c.waiting > 0 ? { state: "waiting", words: "answers waiting" } : reportWaits(c.report) ? { state: "waiting", words: "report waiting" } : { state: "fine" };
const NEED: Record<string, number> = { needsHelp: 0, waiting: 1, fine: 2 };
/** What needs the educator first: help, then answers or a report waiting, then the rest, each in roll order. */
export const needsFirst = (a: ChildRow, b: ChildRow) => NEED[childState(a).state] - NEED[childState(b).state];

export function ClassesTable({ rows, page, pageHref }: { rows: ClassLine[]; page: number; pageHref: (n: number) => string }) {
  const columns: Column<ClassLine>[] = [
    { key: "class", label: "Class", width: "9rem", value: (c) => c.section, cell: (c) => <Link href={`/growth?class=${encodeURIComponent(c.section)}`}>{c.section}</Link> },
    { key: "grade", label: "Grade", width: "8rem", value: (c) => c.grade },
    { key: "children", label: "Children", num: true, width: "6rem", value: (c) => c.kids.length },
    { key: "help", label: "Need help", num: true, width: "6rem", value: (c) => c.kids.filter((k) => k.needs_help > 0).length },
    { key: "waiting", label: "Answers waiting", num: true, width: "7rem", value: (c) => sum(c.kids, (k) => k.waiting) },
    { key: "reports", label: "Parent reports waiting", num: true, width: "8rem", value: (c) => c.kids.filter((k) => reportWaits(k.report)).length },
    { key: "state", label: "Status", status: true, width: "10rem", value: (c) => classState(c.kids), cell: (c) => <StatusChip state={classState(c.kids)} /> },
    {
      key: "skills",
      label: "",
      width: "11rem",
      keep: true,
      value: (c) => c.section,
      cell: (c) => <Link href={`/growth/class/${encodeURIComponent(c.section)}`}>Against every skill →</Link>,
    },
  ];
  return <DataTable label="Classes" columns={columns} rows={rows} rowKey={(c) => c.section} more={{ page, href: pageHref }} />;
}

export function ChildrenTable({ rows, label, withClass, page, pageHref, sort }: { rows: ChildRow[]; label: string; withClass: boolean; page: number; pageHref: (n: number) => string; sort: Sort }) {
  const columns: Column<ChildRow>[] = [
    ...(withClass ? [{ key: "class", label: "Class", width: "7.5rem", value: (r: ChildRow) => r.section } satisfies Column<ChildRow>] : []),
    { key: "roll", sortable: true, label: "Roll", num: true, width: "3.5rem", value: (r) => r.roll_no },
    {
      key: "name",
      sortable: true,
      label: "Child",
      width: "7rem",
      value: (r) => r.first_name,
      cell: (r) => (
        // the one link of the row, stretched over all of it: a click anywhere opens the child
        <Link href={`/growth/${r.id}`} className="font-medium after:absolute after:inset-0 after:content-['']">
          {r.first_name}
        </Link>
      ),
    },
    {
      key: "help",
      sortable: true,
      label: "Needs help on",
      value: (r) => r.help?.name,
      cell: (r) =>
        r.help ? (
          <span>
            {r.help.name}
            {r.help.mistake ? <span className="block text-[12px] text-basalt/65">{r.help.mistake}</span> : null}
          </span>
        ) : null,
    },
    { key: "needs", sortable: true, label: "Needs help", num: true, width: "4.5rem", value: (r) => r.needs_help, cell: (r) => r.needs_help || null },
    { key: "amber", sortable: true, label: "Practising", num: true, width: "5rem", value: (r) => r.amber, cell: (r) => r.amber || null },
    { key: "green", sortable: true, label: "Secure", num: true, width: "4.5rem", value: (r) => r.green, cell: (r) => r.green || null },
    { key: "waiting", sortable: true, label: "Waiting on you", num: true, width: "5rem", value: (r) => r.waiting, cell: (r) => r.waiting || null },
    {
      key: "report",
      sortable: true,
      label: "Parent report",
      width: "6.5rem",
      value: (r) => (reportWaits(r.report) ? reportWords(r.report).short : null),
      cell: (r) => (reportWaits(r.report) ? <span className="text-[13px]">{reportWords(r.report).short}</span> : null),
    },
    { key: "state", label: "Status", status: true, width: "8.5rem", value: (r) => childState(r).state, cell: (r) => <StatusChip {...childState(r)} /> },
  ];
  return <DataTable label={label} columns={columns} rows={rows} rowKey={(r) => r.id} more={{ page, href: pageHref }} sort={sort} extras={{ attrs: (r) => ({ "data-child": r.id, "data-section": r.section, className: "relative cursor-pointer" }) }} />;
}
