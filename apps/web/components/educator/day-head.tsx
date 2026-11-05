import Link from "@/components/link";
import { Icon, type IconName } from "@/lib/icons";
import type { ClassRef, Fortnight } from "@/lib/educator/types";
import { classWords } from "@/lib/voice-types";
import { E } from "@/lib/educator/words";

// What sits above a calendar: step back, back to now, step on; the fortnight and week; her classes; the month's lock.
const STEP = "inline-flex min-h-[var(--tap)] min-w-[var(--tap)] items-center justify-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] px-[var(--space-2)] text-[length:var(--text-label)] font-medium text-[var(--text)] no-underline";

export function Steps({ back, now, on, words }: { back: string; now: string; on: string; words: { previous: string; next: string; now: string } }) {
  const step = (href: string, label: string, icon?: IconName) => (
    <Link href={href} className={STEP} aria-label={label} title={label}>
      {icon ? <Icon name={icon} /> : label}
    </Link>
  );
  return (
    <div className="flex items-center gap-[var(--space-2)]">
      {step(back, words.previous, "previous")}
      {step(now, words.now)}
      {step(on, words.next, "following")}
    </div>
  );
}

export function Where({ fortnight, week, frozen }: { fortnight: Fortnight | null; week: "A" | "B" | null; frozen: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-[var(--space-2)] text-[length:var(--text-label)] text-[var(--text-muted)]">
      {fortnight ? <span className="rounded-[var(--radius-pill)] bg-[var(--sunken)] px-[var(--space-2)] py-[var(--space-1)]">{E.fortnight(fortnight.number, week)}</span> : null}
      {frozen ? (
        <span data-frozen title={E.frozenNote} className="inline-flex items-center gap-[var(--space-1)]">
          <Icon name="frozen" size={16} />
          {E.frozen}
        </span>
      ) : null}
    </div>
  );
}

/** Her classes, when she holds more than one; one class shows nothing. */
export function ClassPick({ classes, on, href }: { classes: ClassRef[]; on: string; href: (id: string) => string }) {
  if (classes.length < 2) return null;
  return (
    <nav aria-label={E.pickClass} className="mb-[var(--space-3)] flex flex-wrap gap-[var(--space-2)]">
      {classes.map((c) => (
        <Link key={c.id} href={href(c.id)} aria-current={c.id === on ? "page" : undefined} className={`${STEP} ${c.id === on ? "border-[var(--chip-donow-bd)] bg-[var(--chip-donow-bg)] text-[var(--chip-donow-fg)]" : ""}`}>
          {classWords(c)}
        </Link>
      ))}
    </nav>
  );
}
