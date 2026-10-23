import type { CurriculumRow } from "./queries-curriculum";

// The curriculum as a list of skills (goals/uxn2-curriculum-table.yaml): one row per skill of a grade, the grade, subject
// and topic beside it as columns, never as a tree to open. Subject-agnostic: the subject is the tree's own word.
export type SkillLine = {
  id: string;
  grade: string;
  gradeCode: string;
  subject: string;
  topic: string;
  topicCode: string;
  skill: string;
  /** Its short name, the second line of the skill's cell. */
  name: string;
  href: string;
  /** The school's levels this grade holds of the skill, in order. */
  levels: string[];
  approved: boolean;
  /** No class the person sees has been taught it (goals/f1f-taught-per-class.yaml). */
  notTaught: boolean;
  topicOf: string;
  skillCode: string;
  untaught: string[];
};

export type Status = "toApprove" | "approved" | "notTaught";
export const STATUS_WORDS: readonly (readonly [Status, string])[] = [
  ["toApprove", "To approve"],
  ["approved", "Approved"],
  ["notTaught", "Not taught yet"],
];

/** A skill's one state in this list: waiting for approval first (it needs a person), then not yet taught, else approved. */
export const statusOf = (
  l: Pick<SkillLine, "approved" | "notTaught">,
): Status =>
  !l.approved ? "toApprove" : l.notTaught ? "notTaught" : "approved";

export function skillLines(
  rows: CurriculumRow[],
  order: string[],
): SkillLine[] {
  const byId = new Map(rows.map((r) => [r.id, r]));
  return rows
    .filter((r) => r.depth === 3)
    .map((r) => {
      const topic = byId.get(r.parent!)!;
      const subject = byId.get(topic.parent!)!;
      const grade = byId.get(subject.parent!)!;
      return {
        id: r.id,
        grade: grade.label,
        gradeCode: grade.id,
        subject: subject.label,
        topic: topic.label,
        topicCode: r.topic ?? "",
        skill: r.label,
        name: r.sub ?? "",
        href: r.href ?? "",
        levels: order.filter((d) => r.levels[d] != null),
        approved: !r.draft,
        notTaught: !!r.off,
        topicOf: r.topic ?? "",
        skillCode: r.skill ?? "",
        untaught: r.untaught ?? [],
      };
    });
}

export type Chosen = {
  grade?: string;
  subject?: string;
  topic?: string;
  status?: string;
  q?: string;
};

/** The lines the filters keep, the ones that need a person first (to approve), then in the school's own order. */
export function chosen(lines: SkillLine[], f: Chosen): SkillLine[] {
  const q = f.q?.trim().toLowerCase();
  const keep = lines.filter(
    (l) =>
      (!f.grade || l.gradeCode === f.grade) &&
      (!f.subject || l.subject === f.subject) &&
      (!f.topic || l.topicCode === f.topic) &&
      (!f.status || statusOf(l) === f.status) &&
      (!q || `${l.skill} ${l.name} ${l.topic}`.toLowerCase().includes(q)),
  );
  const rank = (l: SkillLine) => (statusOf(l) === "toApprove" ? 0 : 1);
  return keep
    .map((l, i) => [l, i] as const)
    .sort((a, b) => rank(a[0]) - rank(b[0]) || a[1] - b[1])
    .map(([l]) => l);
}
