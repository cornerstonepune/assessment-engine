import { ICON_SIZE, Icon } from "@/lib/icons";
import { childState } from "@/lib/k2-child";
import { TONE_CLASS } from "./status-chip";

// A child's state on a skill: an icon, the school's words, and olive, amber or monsoon. Never terracotta (D-075: red is
// work that is late or missing, never a child). `state` is the engine's code; the words are lib/k2-child.ts's.
export function ChildStateChip({ state, level, compact }: { state: string; level?: number | null; compact?: boolean }) {
  const s = childState(state);
  return (
    <span data-child-state={state} data-tone={s.tone} className={`inline-flex items-center border py-[3px] whitespace-nowrap ${compact ? "gap-[4px] px-[6px] text-[11.5px]" : "gap-[5px] px-[9px] text-[12px]"} ${TONE_CLASS[s.tone]}`}>
      <Icon name={s.icon} size={ICON_SIZE.table} />
      {s.words}
      {level === null || level === undefined ? "" : ` · level ${level}`}
    </span>
  );
}
