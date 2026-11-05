import Link from "@/components/link";
import { Icon } from "@/lib/icons";
import type { Chip } from "@/lib/educator/chip";
import { timeOf } from "@/lib/educator/period";
import type { Period } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";
import { CHIP, ChipTag } from "./tags";

// One period as a calendar block (Today's day and This week's grid): its time as time, what it is in the school's words,
// and its state's colour down its edge with the chip; a break is quiet, an empty slot says Free. Every block opens the
// period. `compact` is the week grid's cell; `chip` is the page's own `chipOf` for it.
export function PeriodBlock({ p, href, chip, compact = false }: { p: Period; href: string; chip: Chip | null; compact?: boolean }) {
  const time = timeOf(p);
  if (p.kind === "empty")
    return (
      <div id={`p-${p.period_id}`} data-period={p.period_id} data-kind="empty" className="grid min-h-[var(--tap)] content-center rounded-[var(--radius-m)] border border-dashed border-[var(--border)] px-[var(--space-2)] text-[length:var(--text-label)] text-[var(--text-muted)]">
        <span className="tabular-nums">{time}</span>
        <span>{E.free}</span>
      </div>
    );
  const fixed = p.kind === "fixed";
  const title = p.name;
  const what = p.activity?.name ?? (fixed ? null : p.line);
  return (
    <Link
      href={href}
      id={`p-${p.period_id}`}
      data-period={p.period_id}
      data-kind={p.kind}
      data-state={chip ?? "none"}
      className="group grid min-h-[var(--tap)] gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border)] border-l-[length:var(--space-1)] bg-[var(--surface)] px-[var(--space-2)] py-[var(--space-2)] text-[var(--text)] no-underline hover:border-[var(--border-control)]"
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
