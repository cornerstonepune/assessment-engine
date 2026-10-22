import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { grades } from "@/lib/queries";
import { type ClassLine, classLines } from "@/lib/queries-staff";
import type { Column } from "@/lib/ux-rules";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// School (goals/uxn2-staff-and-school.yaml): the school's classes, a class to a row: its grade, the children in it and
// who teaches it. Read from the child list and the staff list; nothing new is kept.
export default async function SchoolPage({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  const [lines, g] = await Promise.all([classLines(), grades()]);
  const words = new Map(g.list.map((x) => [x.code, x.name]));
  const text = q.q?.trim().toLowerCase();
  const shown = lines.filter(
    (l) =>
      (!q.grade || l.band === q.grade) &&
      (!text ||
        `${l.section} ${l.teachers.join(" ")}`.toLowerCase().includes(text)),
  );
  const page = Math.max(1, Number(q.page) || 1);
  const columns: Column<ClassLine>[] = [
    {
      key: "class",
      label: "Class",
      width: "9rem",
      keep: true,
      value: (l) => l.section,
      cell: (l) => (
        <Link href={`/growth/class/${encodeURIComponent(l.section)}`}>
          {l.section}
        </Link>
      ),
    },
    {
      key: "grade",
      label: "Grade",
      width: "9rem",
      keep: true,
      value: (l) => words.get(l.band) ?? l.band,
    },
    {
      key: "children",
      label: "Children",
      width: "7rem",
      num: true,
      keep: true,
      value: (l) => l.children,
    },
    {
      key: "teachers",
      label: "Taught by",
      keep: true,
      value: (l) => l.teachers.join(", ") || "No one yet",
    },
  ];
  return (
    <PageShell
      stage="School"
      title="School"
      purpose="The school's classes: each one's grade, the children in it and who teaches it."
      action={
        <Link href="/staff" className="btn">
          Change who teaches which class
        </Link>
      }
      next={{ href: "/growth", label: "Children" }}
    >
      <FilterBar
        action="/school"
        filters={[
          {
            name: "grade",
            label: "Grade",
            value: q.grade,
            all: "Every grade",
            options: g.list
              .filter((x) => lines.some((l) => l.band === x.code))
              .map((x) => [x.code, x.name] as const),
          },
        ]}
        search={{
          name: "q",
          value: q.q,
          placeholder: "Find a class or a teacher",
        }}
      />
      <DataTable
        label="Classes"
        columns={columns}
        rows={shown}
        rowKey={(l) => l.section}
        more={{
          page,
          href: (n: number) =>
            `/school?${new URLSearchParams({ ...(q.grade ? { grade: q.grade } : {}), ...(q.q ? { q: q.q } : {}), ...(n > 1 ? { page: String(n) } : {}) })}`,
        }}
      />
      {shown.length === 0 ? (
        <p className="note mt-2">No class matches these filters.</p>
      ) : null}
    </PageShell>
  );
}
