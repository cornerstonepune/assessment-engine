// One part of an activity page, as the engine reads it (POST /curriculum/page/read, docs/notes/m1-12b-apply-and-edit.md):
// the shapes and the school's words for the eight parts. Pure, so a screen on the server or the browser may import it;
// the component that draws a part is components/page-part/part.tsx.
export const PART_KEYS = ["objective", "materials", "steps", "thinking", "level_0", "level_1", "level_2", "level_3"] as const;
export type PartKey = (typeof PART_KEYS)[number];

export const PART_WORDS: Record<PartKey, string> = {
  objective: "Objective",
  materials: "Materials",
  steps: "Steps",
  thinking: "How to think about it",
  level_0: "Level 0",
  level_1: "Level 1",
  level_2: "Level 2",
  level_3: "Level 3",
};

export type Slip = { keyword: string; spot: string };
export type PagePart = {
  part: PartKey;
  kind: "bullets" | "thinking" | "text";
  /** Whose words: the school's, a draft waiting for a person, or a person's; empty when the part has no words. */
  source: "school" | "drafted" | "person" | "";
  check_me: boolean;
  text: string;
  /** The steps, one bullet each. */
  items: string[];
  /** The thinking's idea line, when a draft's list is current; null for the school's prose. */
  idea: string | null;
  slips: Slip[];
};
