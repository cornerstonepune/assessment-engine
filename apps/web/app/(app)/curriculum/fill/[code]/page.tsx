import { notFound } from "next/navigation";
import { gate, readPage } from "@/lib/curriculum-screens";
import { Chrome } from "../../chrome";
import { PartCard } from "../../parts";

// One activity with every part, who wrote it, and Keep / Edit / Send back on the drafted ones.
export default async function ActivityFill({ params, searchParams }: { params: Promise<{ code: string }>; searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await gate();
  const { code } = await params;
  const q = await searchParams;
  const page = await readPage(me, decodeURIComponent(code));
  if (!page) notFound();
  const back = `/curriculum/fill/${page.code}`;
  return (
    <Chrome here="/curriculum/browse" crumb={page.code} title={page.name} lead={`${page.code} · ${page.section}`}>
      <div className="cs-grid">
        {page.parts.map((p) => (
          <div key={p.part} className="cs-col-8" style={{ gridColumn: "span 12" }}>
            <PartCard part={p} code={page.code} back={back} editing={q.edit === p.part} editHref={`${back}?edit=${p.part}`} />
          </div>
        ))}
      </div>
    </Chrome>
  );
}
