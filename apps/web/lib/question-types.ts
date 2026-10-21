import { sql } from "./db";

// The question types' words and how each prints, as the school's rows say them (goals/b2-question-types-are-rows.yaml):
// every type of one printed format shows that format's words, so a page keyed by `item.fmt` reads them by format. No
// page names a type; a new one is an insert.

export type QuestionKinds = {
  /** A printed format's words: "column sum", "find the mistake". */
  words: Record<string, string>;
  /** Whether a printed format's questions print a sentence of their own, or a line drawn from their numbers. */
  ownWords: Record<string, boolean>;
};

export async function questionKinds(): Promise<QuestionKinds> {
  const rows = await sql<{ fmt: string; words: string; own_words: boolean }[]>`
    select distinct on (fmt) fmt, words, own_words from question_type order by fmt, code`;
  return {
    words: Object.fromEntries(rows.map((r) => [r.fmt, r.words])),
    ownWords: Object.fromEntries(rows.map((r) => [r.fmt, r.own_words])),
  };
}
