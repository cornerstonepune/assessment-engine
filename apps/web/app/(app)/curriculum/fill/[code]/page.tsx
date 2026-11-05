import { requireStaff } from "@/lib/auth";
import { notFound } from "next/navigation";
import { mustBeOn, readPage } from "@/lib/curriculum-screens";
import { PageShell } from "@/components/page-shell";
import Link from "@/components/link";
import { Chrome } from "../../chrome";
import { PartCard } from "../../parts";

// One activity with every part, who wrote it, and Keep / Edit / Send back on the drafted ones.
export default async function ActivityFill({ params, searchParams }: { params: Promise<{ code: string }>; searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  const { reviews } = await mustBeOn(me.email);
  const { code } = await params;
  const q = await searchParams;
  const page = await readPage(me, decodeURIComponent(code));
  if (!page) notFound();
  const back = `/curriculum/fill/${page.code}`;
  return (
    <PageShell
      stage={`Curriculum · ${page.section}`}
      title={page.name}
      purpose={page.code}
      action={<Link href="/curriculum/fill/walk" className="btn">Check the drafted parts</Link>}
      next={{ href: "/curriculum/browse", label: "Back to the curriculum browser" }}
    >
      <Chrome here="/curriculum/browse" crumb={page.code}>
      <div className="cs-stack">
        {page.parts.map((p) => (
          <PartCard key={p.part} part={p} code={page.code} back={back} editing={q.edit === p.part} editHref={`${back}?edit=${p.part}`} readOnly={!reviews} />
        ))}
      </div>
      </Chrome>
    </PageShell>
  );
}
