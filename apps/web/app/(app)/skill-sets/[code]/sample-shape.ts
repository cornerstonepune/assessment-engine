// What the sample form and its actions share (goals/edt_edit_samples_and_kinds.yaml), apart from both: a "use client"
// module's values reach a server page only as client references, and a "use server" one may export only actions.

/** A sample as its form shows it, from the engine (`GET /skill/{code}/sample/form`). */
export type SampleInitial = {
  fields: Record<string, string>;
  wrong: { answer: string; mistake_code: string }[];
  passage_code: string | null;
  rubric_code: string | null;
};

export const BLANK: SampleInitial = { fields: {}, wrong: [], passage_code: null, rubric_code: null };

/** The passage choice that says "I wrote one". */
export const NEW_PASSAGE = "new";
