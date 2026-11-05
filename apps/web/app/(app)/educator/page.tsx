import { PageShell } from "@/components/page-shell";
import { EmptyState } from "@/components/empty-state";
import { PeriodBlock } from "@/components/educator/block";
import { Crumbs } from "@/components/educator/crumbs";
import { ClassPick, DayHead } from "@/components/educator/day-head";
import { Summary } from "@/components/educator/summary";
import { ChipTag, Legend, Pill } from "@/components/educator/tags";
import { requireStaff } from "@/lib/auth";
import { chipOf, countdown, nowAt } from "@/lib/educator/chip";
import { longDate, nowAtSchool, schoolDay, whenIs } from "@/lib/educator/clock";
import { dayOf } from "@/lib/educator/data";
import { blankWords, isBlank, isDay, isLesson, timeOf } from "@/lib/educator/period";
import { notFound } from "next/navigation";
import type { Day } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// Her day as a calendar (M1-09, D-075): the periods down the day, each a block with its time and the school's words,
// coloured by its state; beside it, what is next and the colour key. From M1-06's /timetable/day.
export default async function TodayPage({ searchParams }: { searchParams: Promise<{ class?: string; day?: string; go?: string }> }) {
  const me = await requireStaff();
  const q = await searchParams;
  const today = schoolToday();
  if (q.day !== undefined && !isDay(q.day)) notFound();
  const asked = q.go === "tomorrow" ? schoolDay(q.day ?? today, 1) : (q.day ?? today);
  const d = await dayOf(me, { class_id: q.class, day: asked });
  const at = (day: string) => `/educator?class=${d.class.id}&day=${day}`;
  return (
    <PageShell
      stage={E.area}
      title={d.day === today ? E.today.title : longDate(d.day)}
      purpose={E.today.purpose}
      action={<DayHead back={at(schoolDay(d.day, -1))} now={at(today)} on={at(schoolDay(d.day, 1))} words={E.day} where={d} />}
      next={{ href: `/educator/week?class=${d.class.id}&day=${d.day}`, label: E.week.title }}
    >
      <Crumbs trail={[{ label: E.area }, { label: E.today.title, href: at(today) }, { label: longDate(d.day) }]} />
      <ClassPick classes={d.classes} on={d.class.id} href={(id) => `/educator?class=${id}&day=${d.day}`} />
      <DayCalendar d={d} />
    </PageShell>
  );
}

function DayCalendar({ d }: { d: Day }) {
  if (isBlank(d)) return <EmptyState>{blankWords(d)}</EmptyState>;
  const when = whenIs(d.day);
  const now = nowAtSchool();
  const periods = d.periods;
  const work = periods.map((p) => ({ p, chip: chipOf(p, { now, day: when }) }));
  const lessons = d.periods.filter(isLesson);
  const next = work.find((w) => w.chip === "doNow") ?? (when === "past" ? undefined : work.find((w) => isLesson(w.p) && (when === "future" || w.p.starts_at > now)));
  const line = when === "today" ? nowAt(periods, now) : null;
  const href = (id: string) => `/educator/period/${id}?class=${d.class.id}&day=${d.day}`;
  const first = (ps: typeof d.periods) => (ps[0] ? `#p-${ps[0].period_id}` : undefined);
  const breaks = d.periods.filter((p) => p.kind === "fixed");
  const acts = d.periods.filter((p) => p.activity);
  return (
    <div className="grid grid-cols-12 gap-[var(--space-4)]">
      <div className="col-span-12 max-lg:order-[-2]">
        <Summary
          items={[
            { label: E.counts.periods, n: d.periods.length, href: first(d.periods) },
            { label: E.counts.lessons, n: lessons.length, href: first(lessons) },
            { label: E.counts.breaks, n: breaks.length, href: first(breaks) },
            { label: E.counts.activities, n: acts.length, href: first(acts) },
          ]}
        />
      </div>
      <ol data-day={d.day} data-day-kind={d.kind} aria-label={longDate(d.day)} className="col-span-12 grid gap-[var(--space-2)] lg:col-span-8">
        {d.note?.startsWith("undecided:") ? <li className="text-[length:var(--text-label)] text-[var(--text-muted)]">{E.dayKind.undecided}</li> : null}
        {work.map(({ p, chip }, i) => (
          <li key={p.period_id} className="grid gap-[var(--space-2)]">
            {line === i ? <NowLine now={now} /> : null}
            <PeriodBlock p={p} href={href(p.period_id)} chip={chip} />
          </li>
        ))}
        {line === periods.length ? (
          <li>
            <NowLine now={now} />
          </li>
        ) : null}
      </ol>
      <aside aria-label={E.glance} className="col-span-12 grid content-start gap-[var(--space-3)] max-lg:order-[-1] lg:col-span-4">
        <section className="grid gap-[var(--space-2)] rounded-[var(--radius-m)] border border-[var(--border)] p-[var(--space-3)]" data-next>
          <h2 className="text-[length:var(--text-h3)] font-semibold">{E.nextUp}</h2>
          {next ? (
            <>
              <span className="text-[length:var(--text-label)] text-[var(--text-muted)] tabular-nums">{timeOf(next.p)}</span>
              <span className="font-medium">{next.p.activity?.name ?? next.p.line ?? next.p.label}</span>
              {next.chip ? <ChipTag chip={next.chip} /> : null}
              {next.chip !== "doNow" && when === "today" ? <Pill tone="comingUp" fill={false} data-countdown>
                  {countdown(now, next.p.starts_at)}
                </Pill> : null}
            </>
          ) : (
            <p className="text-[var(--text-muted)]">{when === "past" ? E.dayOver : E.nothingLeft}</p>
          )}
        </section>
        <section className="grid gap-[var(--space-2)]">
          <h2 className="text-[length:var(--text-label)] font-medium text-[var(--text-muted)]">{E.legend}</h2>
          <Legend />
        </section>
      </aside>
    </div>
  );
}

function NowLine({ now }: { now: string }) {
  return (
    <div data-now role="separator" aria-label={`${E.now} ${now}`} className="flex items-center gap-[var(--space-2)] text-[length:var(--text-label)] font-semibold text-[var(--chip-donow-bg)]">
      <span className="tabular-nums">
        {E.now} {now}
      </span>
      <span className="h-[var(--space-1)] flex-1 rounded-[var(--radius-pill)] bg-[var(--chip-donow-bg)]" />
    </div>
  );
}
