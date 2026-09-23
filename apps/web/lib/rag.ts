// Red, amber, green, grey — read from the graph's own states, never new numbers (BUILD-ORDER, "the website as the
// teacher's week"). The states are the engine's (`rebuild_child_skill_state`); this only names their colour.
//   red   a repeating mistake, or under half right
//   amber practising: not yet four in five right
//   green got it, or ready to move up
//   grey  fewer than three answers — not enough to say
export type Rag = "red" | "amber" | "green" | "grey";

export const RAG: Record<string, Rag> = {
  patterned_error: "red",
  emerging: "red",
  practising: "amber",
  secure: "green",
  stretch_ready: "green",
  not_enough_yet: "grey",
};

export const RAG_TONE = { red: "terracotta", amber: "bamboo", green: "neem", grey: "monsoon" } as const;

export const RAG_WORDS: Record<Rag, string> = {
  red: "needs help",
  amber: "practising",
  green: "got it",
  grey: "not enough yet",
};

/** The states whose skills a next paper works on: red and amber (`assess/focus.py` LAGGING). */
export const NEEDS_WORK = Object.keys(RAG).filter((s) => RAG[s] === "red" || RAG[s] === "amber");

export const rag = (state: string | null | undefined): Rag => RAG[state ?? "not_enough_yet"] ?? "grey";
