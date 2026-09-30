import { sql } from "./db";
import type { Difficulty, SkillSet } from "./queries";
import { DIFFICULTIES, GRADE_GROUPS, gradeOf, skillSets } from "./queries";

// Curriculum as one tree (goals/u5-curriculum.yaml): grade → subject → skill → level → worksheets. The skills and
// their counts are `skillSets()`'s own; this adds each level's worksheets, in the order they are numbered.
export type CurriculumSkill = SkillSet & { sheets: Record<string, string[]> };

export async function curriculum(): Promise<{ subject: string; skills: CurriculumSkill[] }> {
  const [sets, sheets, [subject]] = await Promise.all([
    skillSets(),
    sql<{ code: string; level: string; codes: string[] }[]>`
      select t.skill_set_code as code, t.difficulty as level, array_agg(t.code order by t.code) as codes
      from sheet_template t
      where t.source = 'library' and t.retired_at is null
      group by t.skill_set_code, t.difficulty`,
    sql<{ name: string }[]>`select name from subject order by code limit 1`,
  ]);
  const by = new Map<string, Record<string, string[]>>();
  for (const s of sheets) by.set(s.code, { ...(by.get(s.code) ?? {}), [s.level]: s.codes });
  return { subject: subject?.name ?? "Mathematics", skills: sets.map((s) => ({ ...s, sheets: by.get(s.code) ?? {} })) };
}

/** One row of the curriculum table (goals/u12-curriculum-table.yaml): a grade, its subject, a topic or a skill, with
 *  the same columns at every depth — a row above a skill adds up the skills under it. */
export type CurriculumRow = {
  id: string;
  parent: string | null;
  depth: 0 | 1 | 2 | 3;
  label: string;
  /** A skill's short name, its page, and whether it waits for approval. */
  sub?: string;
  href?: string;
  draft?: boolean;
  questions: number;
  worksheets: number;
  /** Questions at each level of this grade; a level another grade holds is null. */
  levels: Partial<Record<Difficulty, number | null>>;
  /** A skill's level sentences, for the counts under them. */
  words?: Partial<Record<Difficulty, string>>;
  children: number;
  /** Taught, from the answers: a skill any child has a checked answer on; above a skill, how many of its skills. */
  taught: number;
  skills: number;
};

/** The curriculum as rows, grade by grade — each skill under every grade one of its levels belongs to, with those
 *  levels only — and each row's children assessed: those with a checked answer on it (`child_skill_state`), counted
 *  once however many of a topic's skills they reached. */
export async function curriculumRows(): Promise<{ subject: string; rows: CurriculumRow[] }> {
  const [{ subject, skills }, reached] = await Promise.all([
    curriculum(),
    sql<{ code: string; kids: string[] }[]>`
      select ss.code, array_agg(distinct s.child_id::text) as kids
      from child_skill_state s join child c on c.id = s.child_id and c.active
      join skill_set ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code
      where s.n_events > 0 group by ss.code`,
  ]);
  const kids = new Map(reached.map((r) => [r.code, r.kids]));
  const rows: CurriculumRow[] = [];
  const sum = (xs: CurriculumRow[], k: "questions" | "worksheets") => xs.reduce((n, x) => n + x[k], 0);
  const levelSums = (xs: CurriculumRow[]) =>
    Object.fromEntries(
      DIFFICULTIES.map((d) => [d, xs.some((x) => x.levels[d] != null) ? xs.reduce((n, x) => n + (x.levels[d] ?? 0), 0) : null]),
    ) as CurriculumRow["levels"];
  for (const [band, words] of GRADE_GROUPS) {
    const inGrade = (s: CurriculumSkill) => DIFFICULTIES.filter((d) => s.difficulty[d] && gradeOf(s, d) === band);
    const group = skills.filter((s) => inGrade(s).length);
    if (!group.length) continue;
    const grade: CurriculumRow = { id: band, parent: null, depth: 0, label: words, questions: 0, worksheets: 0, levels: {}, children: 0, taught: 0, skills: 0 };
    const subj: CurriculumRow = { ...grade, id: `${band}/subject`, parent: band, depth: 1, label: subject };
    const topics = [...new Map(group.map((s) => [s.topic_code ?? "", s])).values()].sort((a, b) => (a.topic_ord ?? 99) - (b.topic_ord ?? 99));
    const topicRows: CurriculumRow[] = [];
    const all = new Set<string>();
    rows.push(grade, subj);
    for (const t of topics) {
      const id = `${band}/${t.topic_code ?? ""}`;
      const skillRows = group
        .filter((s) => s.topic_code === t.topic_code)
        .map((s): CurriculumRow => {
          const levels = inGrade(s);
          return {
            id: `${band}/${s.code}`,
            parent: id,
            depth: 3,
            label: s.learning_objective,
            sub: s.name,
            href: `/skill-sets/${s.code}`,
            draft: s.status !== "ratified",
            questions: levels.reduce((n, d) => n + (s.counts[d] ?? 0), 0),
            worksheets: levels.reduce((n, d) => n + (s.worksheets[d] ?? 0), 0),
            levels: Object.fromEntries(DIFFICULTIES.map((d) => [d, levels.includes(d) ? (s.counts[d] ?? 0) : null])),
            words: Object.fromEntries(levels.map((d) => [d, s.difficulty[d].words])),
            children: kids.get(s.code)?.length ?? 0,
            taught: kids.has(s.code) ? 1 : 0,
            skills: 1,
          };
        });
      const reach = new Set(group.filter((s) => s.topic_code === t.topic_code).flatMap((s) => kids.get(s.code) ?? []));
      reach.forEach((k) => all.add(k));
      const topic: CurriculumRow = {
        id,
        parent: subj.id,
        depth: 2,
        label: t.topic_name ?? "Other",
        questions: sum(skillRows, "questions"),
        worksheets: sum(skillRows, "worksheets"),
        levels: levelSums(skillRows),
        children: reach.size,
        taught: skillRows.reduce((n, r) => n + r.taught, 0),
        skills: skillRows.length,
      };
      topicRows.push(topic);
      rows.push(topic, ...skillRows);
    }
    for (const r of [grade, subj]) {
      Object.assign(r, {
        questions: sum(topicRows, "questions"),
        worksheets: sum(topicRows, "worksheets"),
        levels: levelSums(topicRows),
        children: all.size,
        taught: topicRows.reduce((n, x) => n + x.taught, 0),
        skills: topicRows.reduce((n, x) => n + x.skills, 0),
      });
    }
  }
  return { subject, rows };
}
