import { sql } from "./db";
import type { Rag } from "./rag";

// A child's states and the colours they show in, as the school's rows say them (goals/b0d-states-and-subject-from-tables.yaml,
// ADR 0085): each state's words, colour and order, and every rule about it — whether a next paper works on it, whether it
// has enough answers to say, how severe it is when a skill set takes its worst skill, whether it is ready to move up or
// may be nearly secure. The states are the engine's (`rebuild_child_skill_state`); no page names one.

export type ChildState = {
  code: string;
  words: string;
  colour: Rag;
  needs_work: boolean;
  enough: boolean;
  move_up: boolean;
  nearly: boolean;
};

/** A colour's own words: in a key or a legend ("got it"), and in a count of skills ("3 secure"). */
export type ColourWords = { words: string; count_words: string };

export type States = {
  list: ChildState[];
  /** A skill's state; a skill with none yet is in the one state of too few answers. */
  of: (code: string | null | undefined) => ChildState;
  colours: Record<Rag, ColourWords>;
};

export async function childStates(): Promise<States> {
  const [list, colours] = await Promise.all([
    sql<ChildState[]>`select code, words, colour, needs_work, enough, move_up, nearly from child_state order by ord`,
    sql<(ColourWords & { code: Rag })[]>`select code, words, count_words from state_colour order by ord`,
  ]);
  const by = new Map(list.map((s) => [s.code, s]));
  const fewest = list.find((s) => !s.enough)!;
  return {
    list,
    of: (code) => (code && by.get(code)) || fewest,
    colours: Object.fromEntries(colours.map((c) => [c.code, { words: c.words, count_words: c.count_words }])) as Record<Rag, ColourWords>,
  };
}

/** The words a strong skill set is said with: its own state's when that is strong, else those of the strong state that is
 *  not ready to move up (the report card's "secure"). */
export function strongWords(states: States, code: string | null | undefined): string {
  const s = states.of(code);
  const strong = (x: ChildState) => x.enough && !x.needs_work;
  return (strong(s) ? s : states.list.find((x) => strong(x) && !x.move_up)!).words;
}
