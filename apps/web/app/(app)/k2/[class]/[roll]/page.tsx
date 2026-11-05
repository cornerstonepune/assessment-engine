import Link from "@/components/link";
import { ChildStateChip } from "@/components/child-state-chip";
import { Crumbs } from "@/components/educator/crumbs";
import { PageShell } from "@/components/page-shell";
import { Notice } from "../../notice";
import { requireStaff } from "@/lib/auth";
import { Icon } from "@/lib/icons";
import { dayWords, levelWords, monthWords, TRENDS, type ChildPage } from "@/lib/k2-child";
import { childPage } from "@/lib/k2-reads";

// A K2 child's page (task M1-17), by Sr. No.: where the child is on each skill (the plan), what is ready next, and how the
// child has moved. Numbers and the educator's own words sit side by side. Not seen is never shown as not secure.
export default async function TheChild({ params }: { params: Promise<{ class: string; roll: string }> }) {
  const me = await requireStaff();
  const { class: classId, roll } = await params;
  const got = await childPage(me.email, classId, roll);
  return (
    <PageShell
      stage="Class picture"
      title={`Sr. No. ${roll}${got.ok ? ` · ${got.value.class}` : ""}`}
      purpose="Where this child is on each skill, what is ready next, and how the child has moved over the months."
      action={<Link href={`/k2/${classId}`} className="btn secondary inline-flex items-center gap-1.5"><Icon name="class" />Class picture</Link>}
      next={{ href: `/k2/${classId}`, label: "Back to the class picture" }}
    >
      <Crumbs trail={[{ label: "Children", href: "/k2" }, { label: got.ok ? got.value.class : "Class", href: `/k2/${classId}` }, { label: `Sr. No. ${roll}` }]} />
      {got.ok ? <Child p={got.value} /> : <Notice flush>{got.message}</Notice>}
    </PageShell>
  );
}

function Child({ p }: { p: ChildPage }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <section className="lg:col-span-7" aria-labelledby="plan" data-k2="plan">
        <h2 id="plan" className="mb-2 text-[18px]">Where the child is</h2>
        {p.skills.length === 0 ? <Notice>Not seen on any skill yet. A confirmed note or form puts the first one here.</Notice> : (
          <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {p.skills.map((s) => (
              <li key={s.code} className="flex flex-col gap-1 py-3">
                <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{s.name}</span><ChildStateChip state={s.state} words={s.words} colour={s.colour} level={s.level} /></div>
                <div className="text-[13px]">last seen {dayWords(s.last_seen)}{s.level === null ? "" : ` · ${levelWords(s.level)}`}</div>
                {s.sentence ? <p className="text-[14px]" data-k2="words">“{s.sentence}”</p> : s.sentence_note ? <p className="text-[13px]">{s.sentence_note}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="flex flex-col gap-6 lg:col-span-5">
        <section aria-labelledby="next" data-k2="ready-next">
          <h2 id="next" className="mb-2 text-[18px]">Ready next</h2>
          {p.ready_next.length === 0 ? <Notice>Nothing is suggested yet. This list uses only links between skills that a member of staff has confirmed. A skill with no confirmed link is left out, not judged.</Notice> : (
            <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
              {p.ready_next.map((r) => (
                <li key={r.skill.code} className="py-3">
                  <div className="font-medium">{r.skill.name}</div>
                  <div className="text-[13px]">after {r.because.map((b) => b.before.name).join(", ")}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-labelledby="growth" data-k2="growth">
          <h2 id="growth" className="mb-2 text-[18px]">How the child has moved</h2>
          {p.growth.length === 0 ? <Notice>No level has been named yet, so there is nothing to compare. Months with no note are left blank, not counted as low.</Notice> : (
            <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
              {p.growth.map((g) => (
                <li key={g.skill.code} className="py-3" data-trend={g.trend}>
                  <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{g.skill.name}</span><span className="inline-flex items-center gap-1 text-[13px]"><Icon name={TRENDS[g.trend].icon} size={16} />{TRENDS[g.trend].words}</span></div>
                  <div className="text-[13px]">first seen {dayWords(g.first_seen)} · last seen {dayWords(g.last_seen)}</div>
                  <ol className="mt-1 flex flex-wrap gap-2 text-[13px]">
                    {g.by_month.map((m) => <li key={m.month} className="border border-[var(--border)] px-[var(--space-2)] py-[var(--space-1)]">{monthWords(m.month)}: {levelWords(m.level)}, {m.days} {m.days === 1 ? "day" : "days"}</li>)}
                  </ol>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
