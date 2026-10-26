// Whose pages these are (goals/nav_teacher_scope_and_todo.yaml, goals/nav3_what_needs_doing.yaml). Nimish, 24 Oct 2026: "When a
// teacher logs in, because there is a mapping of grade and subject to the teacher, only their relevant sections open up." The
// staff list maps a person to classes and subjects, and that is all the site holds about what a person looks at: no control at
// the top (Nimish, 26 Oct: "the filter ... in the main menu at the top just needs to go"); each page filters for itself.
// A view, never a permission: every address still opens (lib/access.ts).

export type Person = { classes?: string[]; subjects?: string[] };
export type Subject = { code: string; label: string };

/** The subjects a person's pages show: those the staff list names that the school has; none named is every subject. */
export function subjectsFor(p: Person, all: readonly Subject[]): Subject[] {
  const named = all.filter((s) => p.subjects?.includes(s.code));
  return named.length ? named : [...all];
}
