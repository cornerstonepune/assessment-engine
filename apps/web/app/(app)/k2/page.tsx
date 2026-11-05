import { redirect } from "next/navigation";
import Link from "@/components/link";
import { Crumbs } from "@/components/educator/crumbs";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { k2Classes } from "@/lib/k2-reads";
import { classWords } from "@/lib/voice-types";
import { Notice } from "./notice";

// The children's pictures start from her class (M1-17): one class opens at once; several are a list. The staff preview, who
// holds no class, is offered every class whose timetable is in force today (the engine's rule, as the timetable's).
export default async function Children() {
  const me = await requireStaff();
  const got = await k2Classes(me.email);
  const classes = got.ok ? got.value.classes : [];
  if (classes.length === 1) redirect(`/k2/${classes[0].id}`);
  return (
    <PageShell
      stage="Children"
      title="Children"
      purpose="Where each child is on each skill, class by class."
      action={<Link href="/educator" className="btn secondary">Today</Link>}
      next={{ href: "/educator", label: "Today" }}
    >
      <Crumbs trail={[{ label: "Children" }]} />
      {!got.ok ? (
        <Notice>{got.message}</Notice>
      ) : classes.length === 0 ? (
        <Notice>No K2 class is yours, and none has a timetable in force today.</Notice>
      ) : (
        <ul className="flex flex-wrap gap-[var(--space-2)]" aria-label="Your classes">
          {classes.map((c) => (
            <li key={c.id}>
              <Link href={`/k2/${c.id}`} className="inline-flex min-h-[var(--tap)] items-center rounded-[var(--radius-m)] border border-[var(--border-control)] px-[var(--space-3)] text-[var(--text)] no-underline">
                {classWords(c)}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
