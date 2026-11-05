import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { Crumbs } from "@/components/educator/crumbs";
import { Where } from "@/components/educator/day-head";
import { Summary } from "@/components/educator/summary";
import { ChipTag } from "@/components/educator/tags";
import { requireStaff } from "@/lib/auth";
import { chipOf } from "@/lib/educator/chip";
import { longDate, nowAtSchool, whenIs } from "@/lib/educator/clock";
import { periodOf } from "@/lib/educator/data";
import { isDay, timeOf } from "@/lib/educator/period";
import { notFound } from "next/navigation";
import { Icon } from "@/lib/icons";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// One period (M1-09), opened from any block of Today or This week: its time, the school's words for it, the planner's
// lines for its subject this fortnight, and its activity. From M1-06's /timetable/period.
const CARD = "grid content-start gap-[var(--space-2)] rounded-[var(--radius-m)] border border-[var(--border)] bg-[var(--surface)] p-[var(--space-3)]";
const HEAD = "flex items-center gap-[var(--space-2)] text-[length:var(--text-h3)] font-semibold";

export default async function PeriodPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ class?: string; day?: string }> }) {
  const me = await requireStaff();
  const [{ id }, q] = await Promise.all([params, searchParams]);
  if (q.day !== undefined && !isDay(q.day)) notFound();
  const p = await periodOf(me, { class_id: q.class, day: q.day ?? schoolToday(), period_id: id });
  const chip = chipOf(p, { now: nowAtSchool(), day: whenIs(p.day) });
  const time = timeOf(p);
  const today = `/educator?class=${p.class.id}&day=${p.day}`;
  const name = p.name;
  return (
    <PageShell
      stage={E.area}
      title={name}
      purpose={E.period.purpose}
      action={
        <div className="flex w-full flex-wrap items-center gap-[var(--space-2)]">
          <span className="inline-flex items-center gap-[var(--space-1)] font-medium tabular-nums">
            <Icon name="time" size={20} />
            {longDate(p.day)} · {time}
          </span>
          {chip ? <ChipTag chip={chip} /> : null}
          <Where fortnight={p.fortnight} week={p.week} frozen={p.frozen} />
        </div>
      }
      next={{ href: today, label: E.today.title }}
    >
      <Crumbs trail={[{ label: E.area }, { label: E.today.title, href: today }, { label: `${time} ${name}` }]} />
      <Summary
        items={[
          { label: E.counts.lines, n: p.plan_lines.length, href: "#planner" },
          { label: E.counts.activities, n: p.activity ? 1 : 0, href: "#activity" },
        ]}
      />
      <div className="grid grid-cols-12 gap-[var(--space-3)]">
        <section className={`${CARD} col-span-12 lg:col-span-6`} data-part="school-words">
          <h2 className={HEAD}>
            <Icon name="school-words" />
            {E.schoolWords}
          </h2>
          <p>{p.text || p.label}</p>
          {p.line ? <p className="text-[var(--text-muted)]">{p.line}</p> : null}
        </section>
        <section className={`${CARD} col-span-12 lg:col-span-6`} id="activity" data-part="activity">
          <h2 className={HEAD}>
            <Icon name="activity" />
            {E.activity}
          </h2>
          {p.activity ? (
            <>
              <p className="font-medium">{p.activity.name}</p>
              <Link href={`/educator/activity/${encodeURIComponent(p.activity.code)}?back=${encodeURIComponent(today)}`} data-open-activity className="inline-flex min-h-[var(--tap)] w-fit items-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border-control)] px-[var(--space-3)] font-medium text-[var(--text)] no-underline">
                <Icon name="next" size={16} />
                {E.page.open}
              </Link>
            </>
          ) : (
            <p className="text-[var(--text-muted)]">{E.noActivity}</p>
          )}
        </section>
        <section className={`${CARD} col-span-12`} id="planner" data-part="planner">
          <h2 className={HEAD}>
            <Icon name="checklist" />
            {E.planner}
          </h2>
          {p.plan_lines.length ? (
            <ul className="grid list-disc gap-[var(--space-1)] pl-[var(--space-4)]">
              {p.plan_lines.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          ) : (
            <p className="text-[var(--text-muted)]">{E.noPlanner}</p>
          )}
        </section>
      </div>
    </PageShell>
  );
}
