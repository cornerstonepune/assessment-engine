import { ICON_SIZE, Icon } from "@/lib/icons";
import { lookOf } from "@/lib/k2-child";
import { TONE_CLASS } from "./status-chip";

// A child's state on a skill: an icon, the school's words (the `child_state` row's, as the engine sends them), and olive,
// amber or monsoon. Never terracotta (D-075: red is work that is late or missing, never a child). `state` is only the code a
// test or a link can find the chip by; nothing here reads it.
export function ChildStateChip({ state, words, colour, level, compact }: { state: string; words: string; colour: string; level?: number | null; compact?: boolean }) {
  const s = lookOf(colour);
  return (
    <span data-child-state={state} data-tone={s.tone} className={`inline-flex items-center border py-[3px] whitespace-nowrap ${compact ? "gap-[4px] px-[6px] text-[11.5px]" : "gap-[5px] px-[9px] text-[12px]"} ${TONE_CLASS[s.tone]}`}>
      <Icon name={s.icon} size={ICON_SIZE.table} />
      {words}
      {level === null || level === undefined ? "" : ` · level ${level}`}
    </span>
  );
}
