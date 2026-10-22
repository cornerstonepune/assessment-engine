import { sql } from "./db";
import { staffList } from "./queries";

// Who teaches which class, read for the Staff and School pages (goals/uxn2-staff-and-school.yaml). A person's password
// hash lives in the same list and never leaves it: only the name, email, role and classes are read here.
export type Person = {
  email: string;
  name: string;
  role: string;
  classes: string[];
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
  }));
}

/** Every class a child still in school is in, with its grade and how many children, and the names of those who teach it. */
export async function classLines(): Promise<ClassLine[]> {
  const rows = await sql<{ section: string; band: string; children: number }[]>`
    select section, min(band) as band, count(*)::int as children from child where active group by section order by min(band), section`;
  const staff = await people();
  return rows.map((r) => ({
    ...r,
    teachers: staff
      .filter((p) => p.classes.includes(r.section))
      .map((p) => p.name),
  }));
}
