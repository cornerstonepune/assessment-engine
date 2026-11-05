import { ICON_SIZE, Icon, type IconName } from "@/lib/icons";

// The one chip a state is shown in (docs/ux-rules.md, rule 2 and 9): an icon, the word, and one of red, amber or green,
// from this table alone — never colour by itself. Nimish, 2026-10-22: "use icons or red, amber, green in places that make
// it easier for people to navigate". Red is rare: it means the educator is needed now. `quiet` (grey) is a state with
// nothing to do. A state not in `STATES` is not shown: add it here, with its word and its tone, before a page uses it.
// Blank, wrong and wrong-with-working stay three things (rule 5): three words, three icons.
export const STATES = {
  right: { tone: "ok", words: "right" },
  done: { tone: "ok", words: "done" },
  wrong: { tone: "wait", words: "wrong" },
  blank: { tone: "quiet", words: "blank" },
  waiting: { tone: "wait", words: "waiting" },
  spot: { tone: "quiet", words: "spot-check" },
  unreadable: { tone: "act", words: "could not read" },
  judge: { tone: "act", words: "for you to judge" },
  toApprove: { tone: "wait", words: "to approve" },
  withChildren: { tone: "wait", words: "with the children" },
  toCheck: { tone: "act", words: "to check" },
  toSignOff: { tone: "wait", words: "to sign off" },
  needsHelp: { tone: "act", words: "needs help" },
  // a child's standing on a topic or a skill, by its colour: always shown in its colour's row's words
  // (`state_colour.count_words`, passed as `words`); these are only the colours' names
  standingGreen: { tone: "ok", words: "green" },
  standingAmber: { tone: "wait", words: "amber" },
  standingGrey: { tone: "quiet", words: "grey" },
  notAssessed: { tone: "quiet", words: "not assessed yet" },
  fine: { tone: "ok", words: "doing well" },
  up: { tone: "ok", words: "better" },
  down: { tone: "act", words: "worse" },
  trusted: { tone: "ok", words: "trusted" },
  chooseOne: { tone: "act", words: "choose one" },
  noPaper: { tone: "act", words: "no paper" },
  replaced: { tone: "quiet", words: "replaced by a newer one" },
  approved: { tone: "ok", words: "approved" },
  printed: { tone: "ok", words: "printed" },
  taught: { tone: "ok", words: "taught" },
  notTaught: { tone: "quiet", words: "not taught yet" },
  doNow: { tone: "act", words: "do now" },
  doSoon: { tone: "wait", words: "this week" },
  whenReady: { tone: "ok", words: "when ready" },
  teachingNow: { tone: "wait", words: "teaching now" },
  nextUp: { tone: "quiet", words: "next" },
  gettingThere: { tone: "wait", words: "getting there" },
  noResult: { tone: "quiet", words: "no result yet" },
  next: { tone: "wait", words: "next" },
  notYet: { tone: "quiet", words: "not yet" },
  inUse: { tone: "ok", words: "in use" },
  stopped: { tone: "quiet", words: "stopped" },
  // the K2 voice notes (task M1-04): a note to confirm, one with a problem, one about an earlier day, a child not named
  toConfirm: { tone: "wait", words: "to confirm" },
  fixThis: { tone: "act", words: "fix this" },
  late: { tone: "quiet", words: "late", icon: "late" },
  notSeen: { tone: "quiet", words: "not seen" },
  toDo: { tone: "quiet", words: "to do" },
  reading: { tone: "wait", words: "reading" },
} as const;
export type State = keyof typeof STATES;
export type Tone = (typeof STATES)[State]["tone"];

const GREEN = "text-neem bg-neem/12 border-neem/30";
const AMBER = "text-mud bg-bamboo/22 border-bamboo/45";
const RED = "text-terracotta bg-terracotta/12 border-terracotta/35";
const GREY = "text-monsoon bg-monsoon/12 border-monsoon/30";
export const TONE_CLASS: Record<Tone, string> = { ok: GREEN, wait: AMBER, act: RED, quiet: GREY };

// A different shape for each tone, so a chip reads without its colour: a tick, a clock, a triangle with a mark, a ring.
// The drawings are in lib/icons.tsx, the one lookup of icons, so a new icon library is one file.
const STATUS_ICONS: Record<Tone, IconName> = { ok: "done", wait: "to-confirm", act: "fix-this", quiet: "to-do" };

/** `round`: a piece of work on the K2 screens (the agreed design: work is a round chip, a child a square cell). */
export function StatusChip({ state, note, words, compact, round }: { state: State; note?: string; words?: string; compact?: boolean; round?: boolean }) {
  const s = STATES[state];
  return (
    <span data-status={state} data-tone={s.tone} className={`inline-flex items-center border py-[3px] whitespace-nowrap ${round ? "rounded-full" : ""} ${compact ? "gap-[4px] px-[6px] text-[11.5px]" : "gap-[5px] px-[9px] text-[12px]"} ${TONE_CLASS[s.tone]}`}>
      <Icon name={"icon" in s ? s.icon : STATUS_ICONS[s.tone]} size={ICON_SIZE.table} />
      {words ?? s.words}
      {note ? ` · ${note}` : ""}
    </span>
  );
}
