import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import type { CheckGroup, CheckPaper } from "@/lib/queries-check-groups";
import type { Column } from "@/lib/ux-rules";

export type GroupRow = CheckGroup & { name: string; classWords: string | null };

/** How long an answer has waited, in days, as a person says it. */
const waited = (since: string, now = Date.now()) => {
  const days = Math.floor((now - new Date(since).getTime()) / 86_400_000);
  return days <= 0 ? "today" : days === 1 ? "1 day" : `${days} days`;
};

// What is left to check, one line for each assessment (goals/asm2_by_topic_and_checking.yaml): how many papers wait, how many
// answers are left, the oldest wait; a line opens into its papers, so one assessment is finished before the next is started.
export function GroupsTable({
  rows,
  open,
  names,
  papersPage,
  page,
  openHref,
  pageHref,
  papersPageHref,
}: {
  rows: GroupRow[];
  open?: string;
  /** The children's first names of the open assessment's papers, by paper. */
  names: Map<string, string>;
  papersPage: number;
  page: number;
  openHref: (key: string, isOpen: boolean) => string;
  pageHref: (n: number) => string;
  papersPageHref: (n: number) => string;
}) {
  const columns: Column<GroupRow>[] = [
    {
      key: "assessment",
      label: "Assessment",
      width: "36%",
      keep: true,
      value: (g) => g.name,
      cell: (g) => (
        <Link
          href={openHref(g.key, g.key === open)}
          aria-expanded={g.key === open}
          className={`font-medium text-basalt before:mr-1 before:inline-block before:w-3 before:text-basalt/50 ${g.key === open ? "before:content-['▾']" : "before:content-['▸']"}`}
        >
          {g.name}
        </Link>
      ),
    },
    { key: "class", label: "Class", width: "11%", value: (g) => g.classWords },
    {
      key: "papers",
      label: "Papers waiting",
      width: "11%",
      num: true,
      keep: true,
      value: (g) => g.papers.length,
    },
    {
      key: "answers",
      label: "Answers left",
      width: "10%",
      num: true,
      keep: true,
      value: (g) => g.answers,
    },
    {
      key: "spots",
      label: "Spot-checks",
      width: "9%",
      num: true,
      value: (g) => g.spots,
    },
    {
      key: "oldest",
      label: "Oldest wait",
      width: "9%",
      value: (g) => waited(g.oldest),
    },
    {
      key: "go",
      label: "",
      width: "15%",
      keep: true,
      value: (g) => g.first,
      cell: (g) => (
        <Link
          href={`/capture/check?id=${g.first}`}
          className="btn secondary whitespace-nowrap"
          data-action="check-assessment"
        >
          Start checking
        </Link>
      ),
    },
  ];
  return (
    <DataTable
      label="Left to check, by assessment"
      columns={columns}
      rows={rows}
      rowKey={(g) => g.key}
      more={{ page, href: pageHref }}
      extras={{
        attrs: (g) => ({ "data-assessment": g.key }),
        expand: (g) =>
          g.key === open ? (
            <PapersTable
              group={g}
              names={names}
              page={papersPage}
              pageHref={papersPageHref}
            />
          ) : null,
      }}
    />
  );
}

function PapersTable({
  group,
  names,
  page,
  pageHref,
}: {
  group: GroupRow;
  names: Map<string, string>;
  page: number;
  pageHref: (n: number) => string;
}) {
  const columns: Column<CheckPaper>[] = [
    {
      key: "roll",
      label: "Roll",
      width: "8%",
      num: true,
      value: (p) => p.roll,
    },
    {
      key: "child",
      label: "Child",
      width: "22%",
      value: (p) => names.get(p.paper_id) ?? null,
    },
    { key: "paper", label: "Paper", width: "20%", value: (p) => p.code },
    {
      key: "answers",
      label: "Answers left",
      width: "14%",
      num: true,
      keep: true,
      value: (p) => p.answers,
    },
    {
      key: "spots",
      label: "Spot-checks",
      width: "12%",
      num: true,
      value: (p) => p.spots,
    },
    {
      key: "go",
      label: "",
      keep: true,
      value: (p) => p.first,
      cell: (p) => (
        <Link href={`/capture/check?id=${p.first}`}>Check this</Link>
      ),
    },
  ];
  return (
    <div data-papers-of={group.key}>
      <DataTable
        label={`Papers of ${group.name}`}
        dense
        columns={columns}
        rows={group.papers}
        rowKey={(p) => p.paper_id}
        more={{ page, href: pageHref }}
      />
    </div>
  );
}
