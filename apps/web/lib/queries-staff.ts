import { sql } from "./db";
import { staffList, type Staff } from "./queries";

// Who teaches which class, read for the Staff and School pages (goals/uxn2-staff-and-school.yaml). A person's password
// hash lives in the same list and never leaves it: only the name, email, role and classes are read here.
export type Person = {
  email: string;
  name: string;
  role: string;
  classes: string[];
  /** The subject codes they teach; none named is every subject (nav_teacher_scope_and_todo). */
  subjects: string[];
};
export type ClassLine = {
  section: string;
  band: string;
  children: number;
  teachers: string[];
};

export async function people(): Promise<Person[]> {
  return (await staffList()).map((s) => ({
    email: s.email,
    name: s.name,
    role: s.role,
    classes: [...(s.classes ?? [])].sort(),
    subjects: [...(s.subjects ?? [])].sort(),
  }));
}

/** Every class a child still in school is in, with its grade and how many children, and the names of those who teach it. */
export async function classLines(): Promise<ClassLine[]> {
  const rows = await sql<{ section: string; band: string; children: number }[]>`
    select c.section, c.band, count(*)::int as children
    from child c left join grade g on g.tenant_id = c.tenant_id and g.code = c.band
    where c.active group by c.section, c.band, g.ord order by g.ord, c.section`;
  const staff = await people();
  return rows.map((r) => ({
    ...r,
    teachers: staff
      .filter((p) => p.classes.includes(r.section))
      .map((p) => p.name),
  }));
}

/** The roles a person may be given on the Staff page: those the school's decisions name (`people.decides`), and any
 *  someone on the list already holds — the same rule as `engine staff add` (engine/core/staff.py `roles`). Rows,
 *  never a list in code (rule 1). */
export async function rolesHeld(): Promise<string[]> {
  const [row] = await sql<{ value: Record<string, string[]> }[]>`
    select value from config where key = 'people.decides'`;
  const named = Object.values(row?.value ?? {}).flat();
  const held = (await staffList()).map((p: Staff) => p.role);
  return [...new Set([...named, ...held])].sort();
}
