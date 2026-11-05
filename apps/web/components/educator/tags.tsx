import { Icon, type IconName } from "@/lib/icons";
import type { Chip } from "@/lib/educator/chip";
import { E } from "@/lib/educator/words";

// A piece of work's state: icon + colour + one word, never colour alone (D-062, D-075's fixed colour meanings: olive
// done, amber needs you soon, terracotta late and work only, monsoon coming up, basalt do now). Colours are tokens only.
export const CHIP: Record<Chip, { icon: IconName; fg: string; bg: string; bd: string }> = {
  doNow: { icon: "play", fg: "var(--chip-donow-fg)", bg: "var(--chip-donow-bg)", bd: "var(--chip-donow-bd)" },
  comingUp: { icon: "to-do", fg: "var(--chip-soon-fg)", bg: "var(--chip-soon-bg)", bd: "var(--chip-soon-bd)" },
  done: { icon: "done", fg: "var(--chip-done-fg)", bg: "var(--chip-done-bg)", bd: "var(--chip-done-bd)" },
  late: { icon: "late", fg: "var(--chip-late-fg)", bg: "var(--chip-late-bg)", bd: "var(--chip-late-bd)" },
};

/** The pill every chip, countdown and fortnight is drawn in: a state's colours, or the plain line. */
export function Pill({ tone, fill = true, children, ...rest }: { tone?: Chip; fill?: boolean; children: React.ReactNode } & React.HTMLAttributes<HTMLSpanElement>) {
  const c = tone ? CHIP[tone] : null;
  return (
    <span {...rest} className="inline-flex w-fit items-center gap-[var(--space-1)] rounded-[var(--radius-pill)] border border-[var(--border)] px-[var(--space-2)] py-[var(--space-1)] text-[length:var(--text-label)] leading-[var(--lh-label)] font-medium whitespace-nowrap" style={c ? { color: c.fg, background: fill ? c.bg : undefined, borderColor: c.bd } : undefined}>
      {children}
    </span>
  );
}

export function ChipTag({ chip }: { chip: Chip }) {
  return (
    <Pill tone={chip} data-chip={chip}>
      <Icon name={CHIP[chip].icon} size={16} />
      {E.chips[chip]}
    </Pill>
  );
}

/** The colour key, once per page: every state the timetable can show, in its colour and word (Coming up is the
 * countdown's colour). */
export function Legend() {
  return (
    <div aria-label={E.legend} className="flex flex-wrap gap-[var(--space-2)]">
      {(Object.keys(CHIP) as Chip[]).map((c) => (
        <ChipTag key={c} chip={c} />
      ))}
    </div>
  );
}
