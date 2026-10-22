import { sql } from "./db";
import { grades } from "./queries";

// What the bar at the top of every screen offers (goals/s1-subject-class-and-today.yaml): the school's subjects, as
// rows of `subject`, and its classes, in the grades' order. A subject or a class added to the school is on the bar
// with no change here.

export type Choices = { subjects: { code: string; label: string }[]; classes: { section: string; words: string }[] };

export async function choices(): Promise<Choices> {
  const [subjects, classes, g] = await Promise.all([
    sql<{ code: string; label: string }[]>`select code, coalesce(label, name) as label from subject order by code`,
    sql<{ section: string; band: string }[]>`
      select section, band from (select distinct tenant_id, section, class_band(tenant_id, section) as band from child where active) k
      order by grade_ord(tenant_id, band), section`,
    grades(),
  ]);
  return { subjects, classes: classes.map((c) => ({ section: c.section, words: `${g.name(c.band)} · ${c.section}` })) };
}
