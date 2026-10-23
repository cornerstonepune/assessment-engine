import type { ReactNode } from "react";

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
  noPaper: { tone: "act", words: "no paper" },
  replaced: { tone: "quiet", words: "replaced by a newer one" },
} as const;
export type State = keyof typeof STATES;
export type Tone = (typeof STATES)[State]["tone"];

const GREEN = "text-neem bg-neem/12 border-neem/30";
const AMBER = "text-mud bg-bamboo/22 border-bamboo/45";
const RED = "text-terracotta bg-terracotta/12 border-terracotta/35";
const GREY = "text-monsoon bg-monsoon/12 border-monsoon/30";
export const TONE_CLASS: Record<Tone, string> = { ok: GREEN, wait: AMBER, act: RED, quiet: GREY };

// A different shape for each tone, so a chip reads without its colour: a tick, a clock, a triangle with a mark, a ring.
const STATUS_ICONS: Record<Tone, ReactNode> = {
  ok: <path d="M3.2 8.4l3 3 6.4-6.8" />,
  wait: (
    <>
      <circle cx="8" cy="8" r="5.6" />
      <path d="M8 4.8V8l2.2 1.4" />
    </>
  ),
  act: (
    <>
      <path d="M8 2.4l6 10.6H2z" />
      <path d="M8 6.6v3M8 11.4v.1" />
    </>
  ),
  quiet: <circle cx="8" cy="8" r="4.6" />,
};

function Icon({ tone }: { tone: Tone }) {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" data-icon={tone}>
      {STATUS_ICONS[tone]}
    </svg>
  );
}

export function StatusChip({ state, note, words }: { state: State; note?: string; words?: string }) {
  const s = STATES[state];
  return (
    <span data-status={state} data-tone={s.tone} className={`inline-flex items-center gap-[5px] border px-[9px] py-[3px] text-[12px] whitespace-nowrap ${TONE_CLASS[s.tone]}`}>
      <Icon tone={s.tone} />
      {words ?? s.words}
      {note ? ` · ${note}` : ""}
    </span>
  );
}
