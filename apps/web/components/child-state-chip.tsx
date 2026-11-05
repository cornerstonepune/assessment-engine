import { ICON_SIZE, Icon } from "@/lib/icons";
import { lookOf, type ChildTone } from "@/lib/k2-child";

// A child's state on a skill: an icon, the school's words (the `child_state` row's, as the engine sends them), and olive,
// amber or monsoon from the school's tokens. Never terracotta (D-075: red is work that is late or missing, never a child).
// `state` is only the code a test or a link can find the chip by; nothing here reads it.
const TOKENS: Record<ChildTone, string> = { ok: "done", wait: "confirm", quiet: "soon" };

export function ChildStateChip({ state, words, colour, level, compact }: { state: string; words: string; colour: string; level?: number | null; compact?: boolean }) {
  const s = lookOf(colour);
  const t = TOKENS[s.tone];
  return (
    <span
      data-child-state={state}
      data-tone={s.tone}
      className={`inline-flex items-center rounded-[var(--radius-pill)] border whitespace-nowrap ${compact ? "gap-[var(--space-1)] px-[var(--space-1)] py-[var(--space-1)] text-[length:var(--text-caption)]" : "gap-[var(--space-1)] px-[var(--space-2)] py-[var(--space-1)] text-[length:var(--text-label)] font-medium"}`}
      style={{ color: `var(--chip-${t}-fg)`, background: `var(--chip-${t}-bg)`, borderColor: `var(--chip-${t}-bd)` }}
    >
      <Icon name={s.icon} size={ICON_SIZE.table} />
      {words}
      {level === null || level === undefined ? "" : ` · level ${level}`}
    </span>
  );
}
