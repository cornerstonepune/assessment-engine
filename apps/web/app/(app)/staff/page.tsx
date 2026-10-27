import { FilterBar } from "@/components/filter-bar";
import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { Notice } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { choices } from "@/lib/choices";
import { classLines, people, rolesHeld } from "@/lib/queries-staff";
import { AddPerson } from "./add-person";
import { StaffTable } from "./staff-table";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Why nobody was added, in the words the coordinator reads.
const NOT_ADDED: Record<string, string> = {
  email: "a name and a school email are both needed",
  role: "that role is not one the school names",
  already: "that email is already on the staff list",
};

// Staff (goals/uxn2-staff-and-school.yaml). Nimish, 2026-10-22: "the staff table of who teaches which class and subject
// is edited on a Staff page, not by commands." A table: person, role, classes; the coordinator opens a row's classes,
// ticks the classes and saves. Subjects are kept beside the classes in the same staff row (no schema change), so a person's
// pages open on their own subjects as on their own classes (goals/nav_teacher_scope_and_todo.yaml).
export default async function StaffPage({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  const [all, classes, offered, givable] = await Promise.all([people(), classLines(), choices(), rolesHeld()]);
  const text = q.q?.trim().toLowerCase();
  const shown = all.filter(
    (p) =>
      (!q.role || p.role === q.role) &&
      (!text || `${p.name} ${p.email}`.toLowerCase().includes(text)),
  );
  const roles = [...new Set(all.map((p) => p.role))].sort();
  const page = Math.max(1, Number(q.page) || 1);
  return (
    <PageShell
      stage="School"
      title="Staff"
      purpose="Who teaches which class. Open a person's classes, tick the ones they teach and save: their pages open on those classes."
      action={
        <Link href="/school" className="btn">
          See the school&rsquo;s classes
        </Link>
      }
      next={{ href: "/", label: "Curriculum" }}
    >
      {q.saved && q.of === "new" ? (
        <Notice tone="neem">
          {q.saved} is on the staff list, and a link to set their own password is on its way to their email. It works
          once and lasts seven days. Choose their classes and subjects on their row.
        </Notice>
      ) : null}
      {q.saved && q.of !== "new" ? (
        <Notice tone="neem">
          {q.saved}&rsquo;s {q.of === "subjects" ? "subjects" : "classes"} are saved. Their pages open on{" "}
          them from now on.
        </Notice>
      ) : null}
      {q.refused && q.of === "new" ? (
        <Notice tone="terracotta">
          Nobody was added: {NOT_ADDED[q.refused] ?? "that cannot be saved"}.
        </Notice>
      ) : null}
      {q.refused && q.of !== "new" ? (
        <Notice tone="terracotta">
          Nothing changed: {q.of === "subjects" ? `${q.refused} is not a subject of the school` : `no child is in ${q.refused}`}.
        </Notice>
      ) : null}
      <AddPerson roles={givable} />
      <FilterBar
        action="/staff"
        filters={[
          {
            name: "role",
            label: "Role",
            value: q.role,
            all: "Every role",
            options: roles.map((r) => [r, r] as const),
          },
        ]}
        search={{ name: "q", value: q.q, placeholder: "Find a person" }}
      />
      <StaffTable
        people={shown}
        classes={classes}
        subjects={offered.subjects}
        page={page}
        pageHref={(n) =>
          `/staff?${new URLSearchParams({ ...(q.role ? { role: q.role } : {}), ...(q.q ? { q: q.q } : {}), ...(n > 1 ? { page: String(n) } : {}) })}`
        }
      />
      {shown.length === 0 ? (
        <p className="note mt-2">Nobody matches these filters.</p>
      ) : null}
    </PageShell>
  );
}
