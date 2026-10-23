import { sql } from "./db";
import type { Difficulty, SkillSet } from "./queries";
import { levels as schoolLevels } from "./levels";
import { gradeOf, grades, skillSets } from "./queries";
import { inScope, type Scope } from "./scope";
import { taughtByGrade, untaughtByGrade } from "./taught";

// Curriculum as one tree (goals/u5-curriculum.yaml): grade → subject → skill → level → worksheets. The skills and
// their counts are `skillSets()`'s own; this adds each level's worksheets, in the order they are numbered.
export type CurriculumSkill = SkillSet & { sheets: Record<string, string[]> };

export async function curriculum(scope: Scope): Promise<{ skills: CurriculumSkill[] }> {
  const [sets, sheets] = await Promise.all([
    // the whole mapping, taught or not (goals/c1-whole-curriculum.yaml): showing a skill is not putting it on a paper
    skillSets({ untaught: true, scope }),
    sql<{ code: string; level: string; codes: string[] }[]>`
      select t.skill_set_code as code, t.difficulty as level, array_agg(t.code order by t.code) as codes
      from sheet_template t
      where t.source = 'library' and t.retired_at is null
      group by t.skill_set_code, t.difficulty`,
  ]);
  const by = new Map<string, Record<string, string[]>>();
  for (const s of sheets) by.set(s.code, { ...(by.get(s.code) ?? {}), [s.level]: s.codes });
  return { skills: sets.map((s) => ({ ...s, sheets: by.get(s.code) ?? {} })) };
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
  /** Its topic is taught in no class of this grade the person sees (goals/f1f-taught-per-class.yaml): shown, and on
   *  no paper of those classes until an educator says it has been taught. */
  off?: boolean;
  /** Its topic and, on a skill's row, its skill set: what "taught" is said of. */
  topic?: string;
  skill?: string;
  /** The classes of this grade the person sees that have not been taught it (goals/l9-not-taught-is-said-where-it-shows.yaml). */
  untaught?: string[];
  questions: number;
  worksheets: number;
  /** Questions at each level of this grade; a level another grade holds is null. */
  levels: Partial<Record<Difficulty, number | null>>;
  /** A skill's level sentences, for the counts under them. */
  words?: Partial<Record<Difficulty, string>>;
  children: number;
  /** Assessed, from the answers: a skill any child has a checked answer on; above a skill, how many of its skills.
   *  Not "taught", which is what a person said of a class (goals/f1f-taught-per-class.yaml). */
  assessed: number;
  skills: number;
};

/** The curriculum as rows, grade by grade — each skill under every grade one of its levels belongs to, with those
 *  levels only — and each row's children assessed: those of the scope's classes with a checked answer on it
 *  (`child_skill_state`), counted once however many of a topic's skills they reached (goals/ux6-curriculum-for-the-
 *  educator.yaml: an educator counts their own class's). */
export async function curriculumRows(scope: Scope): Promise<{ rows: CurriculumRow[]; order: string[] }> {
  const [{ skills }, reached, taught, untaught, { order }, g] = await Promise.all([
    curriculum(scope),
    // a child assessed on a skill (the graph's word, `child_skill_state`) counts under the grade of each level they answered
    // it at: a skill whose Easy level the school files under Grade 1 is not Grade 1's for a child who answered at Medium
    // (goals/ux8a-numbers-true.yaml). An answer with no question behind it has no level, and counts under the skill's grade.
    sql<{ code: string; grade: string; kids: string[] }[]>`
      select ss.code, a.grade, array_agg(distinct s.child_id::text) as kids
      from child_skill_state s join child c on c.id = s.child_id and c.active
      join skill ss on ss.tenant_id = s.tenant_id and ss.rung_code = s.rung_code
      cross join lateral (
        select distinct coalesce(l.grade, ss.grade) as grade
        from evidence_placed e
        left join item_result ir on ir.id = e.item_result_id
        left join item i on i.id = ir.item_id and i.skill_set_code = ss.code
        left join skill_level l on l.tenant_id = ss.tenant_id and l.skill_code = ss.code and l.difficulty = i.difficulty
        where e.child_id = s.child_id and e.placed_rung = s.rung_code and e.confirmed_by is not null) a
      where s.n_events > 0 and ${inScope(scope, sql`c.section`)} group by ss.code, a.grade`,
    taughtByGrade(scope),
    untaughtByGrade(scope),
    schoolLevels(),
    grades(),
  ]);
  const kids = new Map(reached.map((r) => [`${r.grade}|${r.code}`, r.kids]));
  const rows: CurriculumRow[] = [];
  const sum = (xs: CurriculumRow[], k: "questions" | "worksheets") => xs.reduce((n, x) => n + x[k], 0);
  const levelSums = (xs: CurriculumRow[]) =>
    Object.fromEntries(
      order.map((d) => [d, xs.some((x) => x.levels[d] != null) ? xs.reduce((n, x) => n + (x.levels[d] ?? 0), 0) : null]),
    ) as CurriculumRow["levels"];
  // every grade the school has, in its order (goals/b0b-grades-from-the-table.yaml): one with no level in it has no row
  for (const { code: band, name: words } of g.list) {
    const inGrade = (s: CurriculumSkill) => order.filter((d) => s.difficulty[d] && gradeOf(s, d) === band);
    const group = skills.filter((s) => inGrade(s).length);
    if (!group.length) continue;
    const grade: CurriculumRow = { id: band, parent: null, depth: 0, label: words, questions: 0, worksheets: 0, levels: {}, children: 0, assessed: 0, skills: 0 };
    rows.push(grade);
    const everyone = new Set<string>();
    const subjectRows: CurriculumRow[] = [];
    // a grade's subjects, in the order of their first topic (a school with maths and English shows both, one tree each)
    const subjects = [...new Map([...group].sort((a, b) => (a.topic_ord ?? 99) - (b.topic_ord ?? 99)).map((s) => [s.subject_code ?? "", s])).values()];
    for (const sub of subjects) {
      const inSub = group.filter((s) => (s.subject_code ?? "") === (sub.subject_code ?? ""));
      const subj: CurriculumRow = { ...grade, id: `${band}/${sub.subject_code ?? ""}`, parent: band, depth: 1, label: sub.subject_name ?? "" };
      const topics = [...new Map(inSub.map((s) => [s.topic_code ?? "", s])).values()].sort((a, b) => (a.topic_ord ?? 99) - (b.topic_ord ?? 99));
      const topicRows: CurriculumRow[] = [];
      const all = new Set<string>();
      rows.push(subj);
      for (const t of topics) {
        const id = `${band}/${t.topic_code ?? ""}`;
        const skillRows = inSub
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
              off: !taught(band, s.code),
              topic: s.topic_code ?? undefined,
              skill: s.code,
              untaught: untaught(band, s.code),
              questions: levels.reduce((n, d) => n + (s.counts[d] ?? 0), 0),
              worksheets: levels.reduce((n, d) => n + (s.worksheets[d] ?? 0), 0),
              levels: Object.fromEntries(order.map((d) => [d, levels.includes(d) ? (s.counts[d] ?? 0) : null])),
              words: Object.fromEntries(levels.map((d) => [d, s.difficulty[d].words])),
              children: kids.get(`${band}|${s.code}`)?.length ?? 0,
              assessed: kids.has(`${band}|${s.code}`) ? 1 : 0,
              skills: 1,
            };
          });
        const reach = new Set(inSub.filter((s) => s.topic_code === t.topic_code).flatMap((s) => kids.get(`${band}|${s.code}`) ?? []));
        reach.forEach((k) => all.add(k));
        const topic: CurriculumRow = {
          id,
          parent: subj.id,
          depth: 2,
          label: t.topic_name ?? "Other",
          off: skillRows.every((r) => r.off),
          topic: t.topic_code ?? undefined,
          untaught: [...new Set(skillRows.flatMap((r) => r.untaught ?? []))].sort(),
          questions: sum(skillRows, "questions"),
          worksheets: sum(skillRows, "worksheets"),
          levels: levelSums(skillRows),
          children: reach.size,
          assessed: skillRows.reduce((n, r) => n + r.assessed, 0),
          skills: skillRows.length,
        };
        topicRows.push(topic);
        rows.push(topic, ...skillRows);
      }
      Object.assign(subj, {
        questions: sum(topicRows, "questions"),
        worksheets: sum(topicRows, "worksheets"),
        levels: levelSums(topicRows),
        children: all.size,
        assessed: topicRows.reduce((n, x) => n + x.assessed, 0),
        skills: topicRows.reduce((n, x) => n + x.skills, 0),
      });
      all.forEach((k) => everyone.add(k));
      subjectRows.push(subj);
    }
    Object.assign(grade, {
      questions: sum(subjectRows, "questions"),
      worksheets: sum(subjectRows, "worksheets"),
      levels: levelSums(subjectRows),
      children: everyone.size,
      assessed: subjectRows.reduce((n, x) => n + x.assessed, 0),
      skills: subjectRows.reduce((n, x) => n + x.skills, 0),
    });
  }
  return { rows, order };
}
