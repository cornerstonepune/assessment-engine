import { Icon, type IconName } from "@/lib/icons";
import type { Chip } from "@/lib/educator/chip";
import { E } from "@/lib/educator/words";

// A piece of work's state: icon + colour + one word, never colour alone (D-062, D-075's fixed colour meanings: olive
// done, amber needs you soon, terracotta late and work only, monsoon coming up, basalt do now). Colours are tokens only.
export const CHIP: Record<Chip, { icon: IconName; fg: string; bg: string; bd: string }> = {
  doNow: { icon: "play", fg: "var(--chip-donow-fg)", bg: "var(--chip-donow-bg)", bd: "var(--chip-donow-bd)" },
  toConfirm: { icon: "to-confirm", fg: "var(--chip-confirm-fg)", bg: "var(--chip-confirm-bg)", bd: "var(--chip-confirm-bd)" },
  comingUp: { icon: "to-do", fg: "var(--chip-soon-fg)", bg: "var(--chip-soon-bg)", bd: "var(--chip-soon-bd)" },
  done: { icon: "done", fg: "var(--chip-done-fg)", bg: "var(--chip-done-bg)", bd: "var(--chip-done-bd)" },
  late: { icon: "late", fg: "var(--chip-late-fg)", bg: "var(--chip-late-bg)", bd: "var(--chip-late-bd)" },
};

export function ChipTag({ chip }: { chip: Chip }) {
  const c = CHIP[chip];
  return (
    <span data-chip={chip} className="inline-flex w-fit items-center gap-[var(--space-1)] rounded-[var(--radius-pill)] border px-[var(--space-2)] py-[var(--space-1)] text-[length:var(--text-label)] leading-[var(--lh-label)] font-medium whitespace-nowrap" style={{ color: c.fg, background: c.bg, borderColor: c.bd }}>
      <Icon name={c.icon} size={16} />
      {E.chips[chip]}
    </span>
  );
}

/** The colour key, once per page: every state the page can show, in its colour and word. */
export function Legend() {
  return (
    <div aria-label={E.legend} className="flex flex-wrap gap-[var(--space-2)]">
      {(Object.keys(CHIP) as Chip[]).map((c) => (
        <ChipTag key={c} chip={c} />
      ))}
    </div>
  );
}
