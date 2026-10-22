import { FilterBar } from "@/components/filter-bar";
import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { Notice } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { classLines, people } from "@/lib/queries-staff";
import { StaffTable } from "./staff-table";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Staff (goals/uxn2-staff-and-school.yaml). Nimish, 2026-10-22: "the staff table of who teaches which class and subject
// is edited on a Staff page, not by commands." A table: person, role, classes; the coordinator opens a row's classes,
// ticks the classes and saves. Subject is not kept anywhere yet: it waits for a schema decision, so no column pretends.
export default async function StaffPage({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  const [all, classes] = await Promise.all([people(), classLines()]);
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
          See the school's classes
        </Link>
      }
      next={{ href: "/", label: "Curriculum" }}
    >
      {q.saved ? (
        <Notice tone="neem">
          {q.saved}&rsquo;s classes are saved. Their pages open on them from now
          on.
        </Notice>
      ) : null}
      {q.refused ? (
        <Notice tone="terracotta">
          Nothing changed: no child is in {q.refused}.
        </Notice>
      ) : null}
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
