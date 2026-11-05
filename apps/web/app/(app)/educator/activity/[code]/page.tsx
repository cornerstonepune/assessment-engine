import { PageShell } from "@/components/page-shell";
import { PartView } from "@/components/page-part/part";
import { Answers } from "@/components/educator/page-answers";
import { Crumbs } from "@/components/educator/crumbs";
import { Summary } from "@/components/educator/summary";
import { requireStaff } from "@/lib/auth";
import { openTo, pageOf } from "@/lib/educator/data";
import type { PagePart } from "@/lib/page-part";
import { E } from "@/lib/educator/words";

// An activity's page in the educator's screens (M1-09a, D-076): each part drawn by the shared page-part component (the
// school's words, a draft marked "check me", steps as bullets, how to think as an idea and its slips), a drafted part
// with Keep, Edit and Send back, Levels 0–3 and the materials beside. From M1-12b's page routes; not found unless her
// screens are open to her (the switch, or the staff preview), as every educator page. No person is named on it.
const W = E.page;
const first = (ps: PagePart[]) => (ps[0] ? `#part-${ps[0].part}` : undefined);

function Part({ code, p }: { code: string; p: PagePart }) {
  return (
    <div id={`part-${p.part}`} data-part={p.part} data-check-me={p.check_me || undefined}>
      {p.source === "drafted" ? <PartView part={p} actions={<Answers code={code} p={p} />} /> : <PartView part={p} />}
    </div>
  );
}

export default async function ActivityPage({ params, searchParams }: { params: Promise<{ code: string }>; searchParams: Promise<{ back?: string }> }) {
  const me = await requireStaff();
  const [{ code }, q] = await Promise.all([params, searchParams]);
  await openTo(me);
  const page = await pageOf(me, decodeURIComponent(code));
  const back = q.back?.startsWith("/educator") ? q.back : "/educator";
  const parts = page.parts.filter((p) => p.part !== "materials");
  const main = parts.filter((p) => !p.part.startsWith("level_"));
  const levels = parts.filter((p) => p.part.startsWith("level_"));
  const check = parts.filter((p) => p.check_me);
  const school = parts.filter((p) => p.source === "school");
  return (
    <PageShell
      stage={E.area}
      title={page.name}
      purpose={W.purpose}
      action={<span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{[page.section, page.code].filter(Boolean).join(" · ")}</span>}
      next={{ href: back, label: E.today.title }}
    >
      <Crumbs trail={[{ label: E.area }, { label: E.today.title, href: back }, { label: page.name }]} />
      <Summary
        items={[
          { label: W.counts.parts, n: parts.length, href: first(parts) },
          { label: W.counts.checkMe, n: check.length, href: first(check) },
          { label: W.counts.school, n: school.length, href: first(school) },
        ]}
      />
      <div data-activity={page.code} className="grid grid-cols-12 gap-[var(--space-4)]">
        <div className="col-span-12 grid content-start gap-[var(--space-3)] lg:col-span-8">
          {main.map((p) => (
            <Part key={p.part} code={page.code} p={p} />
          ))}
        </div>
        <aside className="col-span-12 grid content-start gap-[var(--space-3)] lg:col-span-4">
          <h2 className="text-[length:var(--text-h3)] font-semibold">{W.levels}</h2>
          {levels.map((p) => (
            <Part key={p.part} code={page.code} p={p} />
          ))}
          <section id="materials" className="grid gap-[var(--space-2)] rounded-[var(--radius-m)] border border-[var(--border)] p-[var(--space-3)]">
            <h2 className="text-[length:var(--text-h3)] font-semibold">{W.materials}</h2>
            {page.materials.items.length ? (
              <ul className="grid list-disc gap-[var(--space-1)] pl-[var(--space-4)]">
                {page.materials.items.map((m, i) => (
                  <li key={i}>
                    {m.name}
                    {m.quantity !== null ? ` · ${m.quantity} ${m.unit}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="whitespace-pre-line">{page.materials.text || W.empty}</p>
            )}
          </section>
        </aside>
      </div>
    </PageShell>
  );
}
