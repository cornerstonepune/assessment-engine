"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import type { Staff } from "@/lib/queries";

// A coordinator says which classes a member of staff teaches (goals/uxn2-staff-and-school.yaml): what
// `engine staff classes <email> G2 G3` does, from the website. The classes named must be classes a child still in school
// is in, or nothing changes; the person's other fields, their password hash among them, are kept as they are.
export async function setClasses(formData: FormData): Promise<void> {
  await requireStaff();
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const wanted = [
    ...new Set(
      formData
        .getAll("class")
        .map((c) => String(c).trim())
        .filter(Boolean),
    ),
  ].sort();
  const there = new Set(
    (
      await sql<
        { section: string }[]
      >`select distinct section from child where active`
    ).map((r) => r.section),
  );
  const missing = wanted.filter((c) => !there.has(c));
  if (missing.length)
    redirect(`/staff?refused=${encodeURIComponent(missing.join(", "))}`);
  const [row] = await sql<
    { value: Staff[] }[]
  >`select value from config where key = 'app.staff'`;
  const people = row?.value ?? [];
  const person = people.find((p) => p.email.toLowerCase() === email);
  if (!person) redirect("/staff");
  const next = people.map((p) =>
    p === person ? { ...p, classes: wanted } : p,
  );
  await sql`update config set value = ${sql.json(next)} where key = 'app.staff'`;
  revalidatePath("/", "layout");
  redirect(`/staff?saved=${encodeURIComponent(person.name)}`);
}

// A coordinator says which subjects a member of staff teaches (goals/nav_teacher_scope_and_todo.yaml): with their classes,
// what their pages open on. The subjects named must be subjects of the school, or nothing changes; none named is every subject.
export async function setSubjects(formData: FormData): Promise<void> {
  await requireStaff();
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const wanted = [...new Set(formData.getAll("subject").map((c) => String(c).trim()).filter(Boolean))].sort();
  const there = new Set((await sql<{ code: string }[]>`select code from subject`).map((r) => r.code));
  const missing = wanted.filter((c) => !there.has(c));
  if (missing.length) redirect(`/staff?of=subjects&refused=${encodeURIComponent(missing.join(", "))}`);
  const [row] = await sql<{ value: Staff[] }[]>`select value from config where key = 'app.staff'`;
  const people = row?.value ?? [];
  const person = people.find((p) => p.email.toLowerCase() === email);
  if (!person) redirect("/staff");
  const next = people.map((p) => (p === person ? { ...p, subjects: wanted } : p));
  await sql`update config set value = ${sql.json(next)} where key = 'app.staff'`;
  revalidatePath("/", "layout");
  redirect(`/staff?of=subjects&saved=${encodeURIComponent(person.name)}`);
}
