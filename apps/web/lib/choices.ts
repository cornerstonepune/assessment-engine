import { cache } from "react";
import { sql } from "./db";
import { grades } from "./queries";

// What the bar at the top of every screen offers (goals/s1-subject-class-and-today.yaml): the school's subjects, as
// rows of `subject`, and its classes, in the grades' order. A subject or a class added to the school is on the bar
// with no change here.

export type Choices = { subjects: { code: string; label: string }[]; classes: { section: string; words: string }[] };

export const choices = cache(async (): Promise<Choices> => {
  const [subjects, classes, g] = await Promise.all([
    // the first is what a page opens on for someone who has not chosen: a subject with approved skills before one still
    // waiting for its first approval (English's, E0), so the school's site opens where its work is
    sql<{ code: string; label: string }[]>`
      select su.code, coalesce(su.label, su.name) as label from subject su
      order by exists (select 1 from skill s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code
                       where t.tenant_id = su.tenant_id and t.subject_code = su.code and s.status = 'ratified') desc, su.code`,
    sql<{ section: string; band: string }[]>`
      select section, band from (select distinct tenant_id, section, class_band(tenant_id, section) as band from child where active) k
      order by grade_ord(tenant_id, band), section`,
    grades(),
  ]);
  return { subjects, classes: classes.map((c) => ({ section: c.section, words: `${g.name(c.band)} · ${c.section}` })) };
});
