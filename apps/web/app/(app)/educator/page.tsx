import { PageShell } from "@/components/page-shell";
import { EmptyState } from "@/components/empty-state";
import { PeriodBlock } from "@/components/educator/block";
import { Crumbs } from "@/components/educator/crumbs";
import { ClassPick, Steps, Where } from "@/components/educator/day-head";
import { ChipTag, Legend } from "@/components/educator/tags";
import { requireStaff } from "@/lib/auth";
import { chipOf } from "@/lib/educator/chip";
import { longDate, nowAtSchool, schoolDay, whenIs } from "@/lib/educator/clock";
import { dayOf } from "@/lib/educator/data";
import type { Day } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// Her day as a calendar (M1-09, D-075): the periods down the day, each a block with its time and the school's words,
// coloured by its state; beside it, what is next and the colour key. From M1-06's /timetable/day.
export default async function TodayPage({ searchParams }: { searchParams: Promise<{ class?: string; day?: string; go?: string }> }) {
  const me = await requireStaff();
  const q = await searchParams;
  const today = schoolToday();
  const asked = q.go === "tomorrow" ? schoolDay(q.day ?? today, 1) : (q.day ?? today);
  const d = await dayOf(me, { class_id: q.class, day: asked });
  const at = (day: string) => `/educator?class=${d.class.id}&day=${day}`;
  return (
    <PageShell
      stage={E.area}
      title={d.day === today ? E.today.title : longDate(d.day)}
      purpose={E.today.purpose}
      action={
        <div className="flex w-full flex-wrap items-center justify-between gap-[var(--space-2)]">
          <Steps back={at(schoolDay(d.day, -1))} now={at(today)} on={at(schoolDay(d.day, 1))} words={{ previous: E.day.previous, next: E.day.next, now: E.day.today }} />
          <Where fortnight={d.fortnight} week={d.week} frozen={d.frozen} />
        </div>
      }
      next={{ href: `/educator/week?class=${d.class.id}&day=${d.day}`, label: E.week.title }}
    >
      <Crumbs trail={[{ label: E.area }, { label: E.today.title, href: at(today) }, { label: longDate(d.day) }]} />
      <ClassPick classes={d.classes} on={d.class.id} href={(id) => `/educator?class=${id}&day=${d.day}`} />
      <DayCalendar d={d} classId={d.class.id} />
    </PageShell>
  );
}

function DayCalendar({ d, classId }: { d: Day; classId: string }) {
  if (d.kind === "none" || d.kind === "holiday" || d.periods.length === 0)
    return <EmptyState>{d.kind === "holiday" ? `${E.dayKind.holiday}${d.note ? `: ${d.note}` : ""}` : E.dayKind.none}</EmptyState>;
  const when = whenIs(d.day);
  const now = nowAtSchool();
  const work = d.periods.map((p) => ({ p, chip: chipOf(p, { now, day: when }) }));
  const next = work.find((w) => w.chip === "doNow") ?? work.find((w) => w.chip === "comingUp" && (when !== "today" || w.p.starts_at > now));
  const href = (id: string) => `/educator/period/${id}?class=${classId}&day=${d.day}`;
  return (
    <div className="grid grid-cols-12 gap-[var(--space-4)]">
      <ol data-day={d.day} data-day-kind={d.kind} aria-label={longDate(d.day)} className="col-span-12 grid gap-[var(--space-2)] lg:col-span-8">
        {d.note?.startsWith("undecided:") ? <li className="text-[length:var(--text-label)] text-[var(--text-muted)]">{E.dayKind.undecided}</li> : null}
        {d.periods.map((p) => (
          <li key={p.period_id}>
            <PeriodBlock p={p} href={href(p.period_id)} day={when} now={now} />
          </li>
        ))}
      </ol>
      <aside aria-label={E.glance} className="col-span-12 grid content-start gap-[var(--space-3)] lg:col-span-4">
        <section className="grid gap-[var(--space-2)] rounded-[var(--radius-m)] border border-[var(--border)] p-[var(--space-3)]" data-next>
          <h2 className="text-[length:var(--text-h3)] font-semibold">{E.nextUp}</h2>
          {next ? (
            <>
              <span className="text-[length:var(--text-label)] text-[var(--text-muted)] tabular-nums">
                {next.p.starts_at}
                {next.p.ends_at ? `–${next.p.ends_at}` : ""}
              </span>
              <span className="font-medium">{next.p.activity?.name ?? next.p.line ?? next.p.label}</span>
              {next.chip ? <ChipTag chip={next.chip} /> : null}
            </>
          ) : (
            <p className="text-[var(--text-muted)]">{E.nothingLeft}</p>
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
