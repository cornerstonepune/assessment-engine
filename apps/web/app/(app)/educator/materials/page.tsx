import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { EmptyState } from "@/components/empty-state";
import { Crumbs } from "@/components/educator/crumbs";
import { ClassPick } from "@/components/educator/day-head";
import { DataTable } from "@/components/data-table";
import { BTN, FIELD, materialColumns, type DayLine } from "@/components/educator/materials-table";
import { Summary } from "@/components/educator/summary";
import { addLine } from "./actions";
import { requireStaff } from "@/lib/auth";
import { catalogueOf, dayOf, materialsOf, openTo, type Span } from "@/lib/educator/data";
import { isDay } from "@/lib/educator/period";
import { notFound } from "next/navigation";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// Her class's materials (M1-09m, D-076): built by the engine from the activities in the plan, for a day, a week or a
// fortnight from a day; each day a table of its lines, each line tied to its activity. She sets a quantity, removes a
// line, adds from the catalogue. No send here. Room below the tables for M1-16's note and photograph.
const W = E.materials;
const SPANS: Span[] = ["day", "week", "fortnight"];

export default async function MaterialsPage({ searchParams }: { searchParams: Promise<{ class?: string; day?: string; span?: string }> }) {
  const me = await requireStaff();
  const q = await searchParams;
  if (q.day !== undefined && !isDay(q.day)) notFound();
  const day = q.day ?? schoolToday();
  const span: Span = SPANS.includes(q.span as Span) ? (q.span as Span) : "week";
  const d = await dayOf(me, { class_id: q.class, day }); // not found when her screens are closed to her
  const [list, catalogue, { previewing }] = await Promise.all([materialsOf(me, d.class.id, day, span), catalogueOf(me), openTo(me)]);
  const here = (s: Span) => `/educator/materials?class=${d.class.id}&day=${day}&span=${s}`;
  const lines = list?.groups.flatMap((g) => g.lines) ?? [];
  const on = new Set(lines.map((l) => l.material_code));
  return (
    <PageShell
      stage={E.area}
      title={W.title}
      purpose={W.purpose}
      action={
        <nav aria-label={W.title} className="flex flex-wrap gap-[var(--space-2)]">
          {SPANS.map((s) => (
            <Link key={s} href={here(s)} aria-current={s === span ? "page" : undefined} className={`${BTN} no-underline ${s === span ? "border-[var(--chip-donow-bd)] bg-[var(--chip-donow-bg)] text-[var(--chip-donow-fg)]" : ""}`}>
              {W.span[s]}
            </Link>
          ))}
        </nav>
      }
      next={{ href: `/educator?class=${d.class.id}&day=${day}`, label: E.today.title }}
    >
      <Crumbs trail={[{ label: E.area }, { label: W.nav, href: here(span) }, { label: W.classList }]} />
      <ClassPick classes={d.classes} on={d.class.id} href={(id) => `/educator/materials?class=${id}&day=${day}&span=${span}`} />
      {list === null ? (
        <EmptyState>{W.notHers}</EmptyState>
      ) : (
        <>
          <Summary
            items={[
              { label: W.counts.lines, n: lines.length },
              { label: W.counts.days, n: list.groups.length, href: list.groups[0] ? "#lines" : undefined },
              { label: W.counts.noQty, n: lines.filter((l) => l.quantity === null).length },
            ]}
          />
          <div id="lines" className="grid gap-[var(--space-4)]">
            {list.groups.length === 0 ? <EmptyState>{W.none}</EmptyState> : null}
            {list.groups.length ? (
              <DataTable
                label={W.title}
                columns={materialColumns(previewing)}
                rows={list.groups.flatMap((g) => g.lines.map((l): DayLine => ({ ...l, day: g.label })))}
                rowKey={(l) => l.line_id}
                more={{ by: (l) => l.day }}
                extras={{ attrs: (l) => ({ "data-line": l.line_id }) }}
              />
            ) : null}
            {previewing ? null : (
            <form action={addLine} className="flex flex-wrap items-center gap-[var(--space-2)]" data-add>
              <input type="hidden" name="list" value={list.list_id} />
              <input type="hidden" name="day" value={day} />
              <select name="code" aria-label={W.add} defaultValue="" className={FIELD}>
                <option value="">{W.add}</option>
                {catalogue
                  .filter((c) => !on.has(c.code))
                  .map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                    </option>
                  ))}
              </select>
              <button type="submit" className={BTN}>
                {W.addButton}
              </button>
            </form>
            )}
          </div>
        </>
      )}
    </PageShell>
  );
}
