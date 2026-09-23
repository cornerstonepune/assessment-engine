import { sql } from "./db";
import type { SkillSet } from "./queries";
import { skillSets } from "./queries";

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
