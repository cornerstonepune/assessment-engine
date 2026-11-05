import { redirect } from "next/navigation";
import Link from "@/components/link";
import { Crumbs } from "@/components/educator/crumbs";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { myVoice } from "@/lib/voice";
import { classWords } from "@/lib/voice-types";
import { Notice } from "./notice";

// The children's pictures start from her class (M1-17): one class opens at once; several are a list. A member of staff who
// holds no class (the staff preview) opens a class by its address.
export default async function Children() {
  const me = await requireStaff();
  const my = await myVoice(me);
  const classes = my?.classes ?? [];
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
      {classes.length === 0 ? (
        <Notice>You hold no K2 class here. A class opens from its own address.</Notice>
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
