// Whose pages these are (goals/nav_teacher_scope_and_todo.yaml). Nimish, 24 Oct 2026: "When a teacher logs in, because
// there is a mapping of grade and subject to the teacher, only their relevant sections open up." The staff list maps a
// person to classes and subjects; a person mapped to one class and one subject sees that alone and is offered no choice.
// A coordinator (every class) or anyone mapped to more than one subject gets one small "Viewing" control. A view, never a
// permission: every address still opens (lib/access.ts).

export type Person = { classes?: string[]; subjects?: string[] };
export type Subject = { code: string; label: string };

/** Whether the person chooses what they look at: no class named (every class), or more than one subject. */
export function isBroad(p: Person): boolean {
  return !p.classes?.length || (p.subjects?.length ?? 0) > 1;
}

/** The subjects a person's pages show: those the staff list names that the school has; none named is every subject. */
export function subjectsFor(p: Person, all: readonly Subject[]): Subject[] {
  const named = all.filter((s) => p.subjects?.includes(s.code));
  return named.length ? named : [...all];
}

/** The subject a page opens on: the one chosen in the Viewing control if it is one of theirs, else their first. */
export function subjectNow(p: Person, all: readonly Subject[], chosen: string | null | undefined): Subject | undefined {
  const mine = subjectsFor(p, all);
  return mine.find((s) => s.code === chosen) ?? mine[0];
}

/** "Maths · Grade 2 · 2B" as the Viewing control says it. */
export function viewingWords(subject: string | undefined, classes: string[] | null): string {
  const where = classes === null ? "every class" : classes.length > 3 ? `${classes.length} classes` : classes.join(", ");
  return [subject, where].filter(Boolean).join(" · ");
}
