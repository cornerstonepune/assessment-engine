import { sql } from "./db";
import type { Scope } from "./scope";

// Levels to review (goals/cal_levels_to_review.yaml): for each skill and level, for a grade and for one class, how many
// children were assessed, how many are secure, and what that says. The counting is the database's (`level_calibration`,
// ring B: a pure function of the confirmed evidence, using the graph's own rule); the 80 percent and the 8 children are
// rows of `threshold`. This file only reads, and says the counts in words. Nothing here changes a level.

export type Verdict = "too_few" | "review" | "fine";

export type LevelRow = {
  kind: "grade" | "class";
  scope: string;
  grade: string;
  gradeName: string;
  skill: string;
  skillName: string;
  topic: string;
  topicName: string;
  difficulty: string;
  assessed: number;
  secure: number;
  min: number;
  share: number;
  verdict: Verdict;
  lookedAt: string | null;
  lookedBy: string | null;
};

/** The rows a person may see. A class row is shown for each class in their scope; a grade row only to someone whose scope
 *  holds every class of that grade, since it counts the children of them all. Suggestions first, then by topic, skill and
 *  level in the school's order. */
export async function levelRows(scope: Scope): Promise<LevelRow[]> {
  const classes = scope.classes;
  const visible = classes
    ? sql`(l.scope_kind = 'class' and l.scope_value = any(${classes}))
          or (l.scope_kind = 'grade' and not exists (
                select 1 from child c where c.tenant_id = l.tenant_id and c.band = l.scope_value and c.active
                  and c.section <> all(${classes})))`
    : sql`true`;
  return sql<LevelRow[]>`
    select l.scope_kind as kind, l.scope_value as scope, l.grade, g.name as "gradeName", l.skill_code as skill,
           s.name as "skillName", coalesce(s.topic_code, '') as topic, coalesce(t.name, 'Other') as "topicName",
           l.difficulty, l.assessed, l.secure, l.min_children as min, l.share_needed::float as share, l.verdict,
           l.looked_at::text as "lookedAt", l.looked_by as "lookedBy"
    from level_calibration l
    join skill s on s.tenant_id = l.tenant_id and s.code = l.skill_code
    join difficulty d on d.tenant_id = l.tenant_id and d.code = l.difficulty
    join grade g on g.tenant_id = l.tenant_id and g.code = l.grade
    left join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code
    where ${visible}
    order by (l.verdict = 'review' and l.looked_at is null) desc, t.ord nulls last, s.ladder_order nulls last, s.code,
             g.ord, l.scope_value, d.ord`;
}

/** How many suggestions wait for a person: the figure for What needs doing ("Levels to review: N suggestions"). */
export async function levelsToReviewCount(scope: Scope): Promise<number> {
  const rows = await levelRows(scope);
  return rows.filter(isSuggestion).length;
}

export const isSuggestion = (r: LevelRow) => r.verdict === "review" && !r.lookedAt;

/** What was counted, in words: the figures are the database's, never a model's. */
export function saidOf(r: LevelRow): string {
  if (r.verdict === "review" && r.lookedAt) return `${r.secure} of ${r.assessed} children are secure at ${r.difficulty}. Looked at; it comes back if the numbers move.`;
  if (r.verdict === "review")
    return `Most children (${r.secure} of ${r.assessed}) are secure at ${r.difficulty} in ${r.skillName}. Consider making it harder or adding a harder level.`;
  if (r.verdict === "too_few") return `${r.assessed} ${r.assessed === 1 ? "child has" : "children have"} been assessed at ${r.difficulty}; nothing is suggested until ${r.min} have.`;
  return `${r.secure} of ${r.assessed} children are secure at ${r.difficulty}, under ${Math.round(r.share * 100)}%: no change suggested.`;
}

/** "I've looked at this": one row, with the counts the database holds now (never counts a form sent), added to and never
 *  changed. Returns false when the level has no such figures for the scope. */
export async function recordLookedAt(
  by: string,
  what: { kind: "grade" | "class"; scope: string; skill: string; difficulty: string },
): Promise<boolean> {
  const rows = await sql`
    insert into calibration_review (tenant_id, skill_code, difficulty, scope_kind, scope_value, assessed, secure, reviewed_by)
    select l.tenant_id, l.skill_code, l.difficulty, l.scope_kind, l.scope_value, l.assessed, l.secure, ${by}
    from level_calibration l
    where l.scope_kind = ${what.kind} and l.scope_value = ${what.scope} and l.skill_code = ${what.skill}
      and l.difficulty = ${what.difficulty}
    returning id`;
  return rows.length > 0;
}
