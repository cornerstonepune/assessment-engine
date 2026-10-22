import { Pill } from "./shell";

// The one set of states a row or a page can be in, and the one word for each (rule 2). A state not here is not shown:
// add it here, with its word, before a page uses it. Blank, wrong and wrong-with-working stay three things (rule 5).
export const STATES = {
  right: { tone: "neem", words: "right" },
  wrong: { tone: "terracotta", words: "wrong" },
  blank: { tone: "monsoon", words: "blank" },
  unreadable: { tone: "bamboo", words: "could not read" },
  judge: { tone: "bamboo", words: "for you to judge" },
  waiting: { tone: "bamboo", words: "waiting" },
  spot: { tone: "monsoon", words: "spot-check" },
  done: { tone: "neem", words: "done" },
} as const;
export type State = keyof typeof STATES;

export function StatusChip({ state, note }: { state: State; note?: string }) {
  const s = STATES[state];
  return (
    <Pill tone={s.tone}>
      {s.words}
      {note ? ` · ${note}` : ""}
    </Pill>
  );
}
