import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { PeriodBlock } from "@/components/educator/block";
import { Crumbs } from "@/components/educator/crumbs";
import { ClassPick, Steps, Where } from "@/components/educator/day-head";
import { Summary } from "@/components/educator/summary";
import { Legend } from "@/components/educator/tags";
import { requireStaff } from "@/lib/auth";
import { mondayOf, nowAtSchool, shortDate, whenIs } from "@/lib/educator/clock";
import { weekOf } from "@/lib/educator/data";
import type { Week } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// Her week as a calendar (M1-09, D-075): a column a day, a row a period, each cell its block, a holiday one tall cell.
// On a phone the days stand one under another. From M1-06's /timetable/week.
export default async function WeekPage({ searchParams }: { searchParams: Promise<{ class?: string; day?: string; go?: string }> }) {
  const me = await requireStaff();
  const q = await searchParams;
  const today = schoolToday();
  const monday = mondayOf(q.day ?? today, q.go === "next" ? 1 : 0);
  const w = await weekOf(me, { class_id: q.class, week_of: monday });
  const at = (day: string) => `/educator/week?class=${w.class.id}&day=${day}`;
  return (
    <PageShell
      stage={E.area}
      title={w.week_of === mondayOf(today) ? E.week.title : `Week of ${shortDate(w.week_of)}`}
      purpose={E.week.purpose}
      action={
        <div className="flex w-full flex-wrap items-center justify-between gap-[var(--space-2)]">
          <Steps back={at(mondayOf(w.week_of, -1))} now={at(today)} on={at(mondayOf(w.week_of, 1))} words={{ previous: E.weekNav.previous, next: E.weekNav.next, now: E.weekNav.now }} />
          <Where fortnight={w.fortnight} week={w.week} frozen={w.frozen} />
        </div>
      }
      next={{ href: `/educator?class=${w.class.id}&day=${w.week_of}`, label: E.today.title }}
    >
      <Crumbs trail={[{ label: E.area }, { label: E.week.title, href: at(today) }, { label: `Week of ${shortDate(w.week_of)}` }]} />
      <ClassPick classes={w.classes} on={w.class.id} href={(id) => `/educator/week?class=${id}&day=${w.week_of}`} />
      <Summary
        items={[
          { label: E.counts.days, n: w.days.filter((d) => d.kind === "teaching" && d.periods.length).length, href: firstDay(w, (d) => d.kind === "teaching") },
          { label: E.counts.holidays, n: w.days.filter((d) => d.kind === "holiday").length, href: firstDay(w, (d) => d.kind === "holiday") },
          { label: E.counts.lessons, n: w.days.flatMap((d) => d.periods).filter((p) => p.kind !== "fixed" && p.kind !== "empty").length },
          { label: E.counts.activities, n: w.days.flatMap((d) => d.periods).filter((p) => p.activity).length },
        ]}
      />
      <WeekGrid w={w} />
      <div className="mt-[var(--space-4)]">
        <Legend />
      </div>
    </PageShell>
  );
}

const firstDay = (w: Week, is: (d: Week["days"][number]) => boolean) => {
  const d = w.days.find(is);
  return d ? `#day-${d.day}` : undefined;
};

function WeekGrid({ w }: { w: Week }) {
  const starts = [...new Set(w.days.flatMap((d) => d.periods.map((p) => p.starts_at)))].sort();
  const row = (start: string) => starts.indexOf(start) + 2; // row 1 holds the days' names
  const now = nowAtSchool();
  return (
    <div data-week={w.week_of} className="grid gap-[var(--space-2)] md:grid-cols-[repeat(5,minmax(0,1fr))]">
      {w.days.map((d, i) => {
        const col = { "--c": i + 1 } as React.CSSProperties;
        const when = whenIs(d.day);
        return [
          when === "today" ? (
            <div key={`${d.day}-today`} data-today-column aria-hidden style={{ ...col, "--r": `1 / span ${starts.length + 1}` } as React.CSSProperties} className="rounded-[var(--radius-m)] bg-[var(--border)]/45 max-md:hidden md:[grid-column:var(--c)] md:[grid-row:var(--r)]" />
          ) : null,
          <Link
            key={`${d.day}-head`}
            id={`day-${d.day}`}
            href={`/educator?class=${w.class.id}&day=${d.day}`}
            data-day-head={d.day}
            style={{ ...col, "--r": 1 } as React.CSSProperties}
            className="flex min-h-[var(--tap)] items-center justify-between border-b border-[var(--border)] px-[var(--space-2)] font-semibold text-[var(--text)] no-underline max-md:mt-[var(--space-3)] md:[grid-column:var(--c)] md:[grid-row:var(--r)]"
          >
            {shortDate(d.day)}
          </Link>,
          d.kind === "holiday" || d.kind === "none" || d.periods.length === 0 ? (
            <div key={`${d.day}-none`} data-day={d.day} data-day-kind={d.kind} style={{ ...col, "--r": `2 / span ${Math.max(starts.length, 1)}` } as React.CSSProperties} className="grid min-h-[var(--tap)] place-content-center rounded-[var(--radius-m)] border border-dashed border-[var(--border)] p-[var(--space-3)] text-center text-[var(--text-muted)] md:[grid-column:var(--c)] md:[grid-row:var(--r)]">
              {d.kind === "holiday" ? `${E.dayKind.holiday}${d.note ? `: ${d.note}` : ""}` : E.dayKind.none}
            </div>
          ) : (
            d.periods.map((p) => (
              <div key={`${d.day}-${p.period_id}`} data-day={d.day} style={{ ...col, "--r": row(p.starts_at) } as React.CSSProperties} className="min-w-0 md:[grid-column:var(--c)] md:[grid-row:var(--r)]">
                <PeriodBlock p={p} href={`/educator/period/${p.period_id}?class=${w.class.id}&day=${d.day}`} day={when} now={now} compact />
              </div>
            ))
          ),
        ];
      })}
    </div>
  );
}
