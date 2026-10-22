import { sql } from "./db";

/** What skill sets are taught as, in one line: the label of each subject their topics belong to (skill_set → topic →
 *  subject, goals/b0d-states-and-subject-from-tables.yaml) — of the ones given, or, given none, of every skill set the
 *  school has. A subject with no label is said by its name. */
export async function subjectOf(skillSets: string[] = []): Promise<string> {
  const rows = await sql<{ label: string }[]>`
    select coalesce(su.label, su.name) as label
    from subject su
    where exists (select 1 from skill ss join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
                  where t.tenant_id = su.tenant_id and t.subject_code = su.code
                    and (${skillSets.length === 0} or ss.code = any(${skillSets})))
    order by su.code`;
  return rows.map((r) => r.label).join(" · ");
}
