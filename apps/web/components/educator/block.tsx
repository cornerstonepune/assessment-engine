import Link from "@/components/link";
import { Icon } from "@/lib/icons";
import { chipOf } from "@/lib/educator/chip";
import type { Period } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";
import { CHIP, ChipTag } from "./tags";

// One period as a calendar block (Today's day and This week's grid): its time as time, what it is in the school's words,
// and its state's colour down its edge with the chip; a break is quiet, an empty slot says Free. Every block opens the
// period. `compact` is the week grid's cell.
export function PeriodBlock({ p, href, day, now, compact = false }: { p: Period; href: string; day: "past" | "today" | "future"; now: string; compact?: boolean }) {
  const chip = chipOf(p, { now, day });
  const time = `${p.starts_at}${p.ends_at ? `–${p.ends_at}` : ""}`;
  if (p.kind === "empty")
    return (
      <div id={`p-${p.period_id}`} data-period={p.period_id} data-kind="empty" className="grid min-h-[var(--tap)] content-center rounded-[var(--radius-m)] border border-dashed border-[var(--border)] px-[var(--space-2)] text-[length:var(--text-label)] text-[var(--text-muted)]">
        <span className="tabular-nums">{time}</span>
        <span>{E.free}</span>
      </div>
    );
  const fixed = p.kind === "fixed";
  const cut = p.line ? p.text.lastIndexOf(": ") : -1;
  const title = fixed ? p.label : cut > 0 ? p.text.slice(0, cut) : p.text || p.label;
  const what = p.activity?.name ?? (fixed ? null : p.line);
  return (
    <Link
      href={href}
      id={`p-${p.period_id}`}
      data-period={p.period_id}
      data-kind={p.kind}
      data-state={chip ?? "none"}
      className={`group grid min-h-[var(--tap)] gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border)] border-l-[length:var(--space-1)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text)] no-underline hover:border-[var(--border-control)] bg-[var(--surface)]`}
      style={{ borderLeftColor: chip ? CHIP[chip].bd : "var(--border)" }}
    >
      <span className="flex flex-wrap items-center justify-between gap-[var(--space-2)]">
        <span className="inline-flex items-center gap-[var(--space-1)] text-[length:var(--text-label)] text-[var(--text-muted)] tabular-nums">
          {fixed ? <Icon name="break" size={16} /> : null}
          {time}
        </span>
        {chip && !compact ? <ChipTag chip={chip} /> : null}
      </span>
      <span className={`${compact ? "text-[length:var(--text-label)]" : "text-[length:var(--text-body)]"} ${fixed ? "text-[var(--text-muted)]" : "font-medium"}`}>{title}</span>
      {what && !compact ? <span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{what}</span> : null}
      {chip && compact ? <ChipTag chip={chip} /> : null}
    </Link>
  );
}
