import { builtName, nameOf } from "@/lib/assessment-steps";
import { classWords } from "@/lib/needs-you";
import type { Grades } from "@/lib/queries";
import { KIND_WORDS, type AssessmentRow } from "@/lib/queries-papers";
import {
  assessmentKey,
  assessmentTitle,
  type Named,
} from "./assessments-table";

/** The assessments with the name each is shown by: the educator's own where there is one, else built from the rows its sheets
 *  stand on (`builtName`, lib/assessment-steps.ts). `topicName` says a topic's code in the school's words. */
export function namedRows(
  rows: AssessmentRow[],
  ctx: {
    g: Grades;
    topicName: (code: string) => string;
    chosen: Map<string, string>;
    files: Map<string, string[]>;
  },
): Named[] {
  return rows.map((a) => {
    const built = builtName({
      title: assessmentTitle(a),
      topics: a.topics.map(ctx.topicName),
      skills: a.skills,
      levels: a.levels,
      kind: a.kind,
      kinds: KIND_WORDS,
      classWords:
        a.band && a.section
          ? classWords(ctx.g, a.band, a.section)
          : a.band
            ? ctx.g.name(a.band)
            : null,
      roll: a.roll,
      day: a.day,
    });
    const key = assessmentKey(a);
    return {
      ...a,
      name: nameOf(ctx.chosen.get(key), built),
      files: ctx.files.get(key) ?? [],
    };
  });
}

/** A file read that belongs to no assessment, as a row of its own: nothing of an assessment, and its file's name. */
export const ghostRow = (file: string): Named => ({
  kind: "earlier",
  section: null,
  band: null,
  week: null,
  set: null,
  title: "",
  subject: null,
  qrs: [],
  copies: 0,
  spares: 0,
  extras: 0,
  waiting: 0,
  right: 0,
  scored: 0,
  unread: 0,
  day: null,
  levels: [],
  signId: null,
  topics: [],
  skills: [],
  roll: null,
  by: { made: 0, printed: 0, scanned: 0, checked: 0, "signed off": 0, replaced: 0 },
  name: "Not matched to an assessment",
  files: [],
  ghost: file,
});
