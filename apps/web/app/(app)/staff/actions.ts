"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { sendFirstLink } from "@/lib/password-actions";
import { rolesHeld } from "@/lib/queries-staff";
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

// A coordinator adds a member of staff (goals/auth-email-password.yaml). Nobody types or sees anyone else's password:
// the person is put on the list without one and emailed a link that lets them set their own, good for
// `password_link.first_days` days. Their classes and subjects are chosen afterwards, on their row.
export async function addPerson(formData: FormData): Promise<void> {
  await requireStaff();
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const name = String(formData.get("name") ?? "").trim();
  const role = String(formData.get("role") ?? "").trim();
  if (!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) redirect("/staff?of=new&refused=email");
  if (!(await rolesHeld()).includes(role)) redirect("/staff?of=new&refused=role");
  // one statement, and it does nothing at all if that email is already on the list: two coordinators adding at once
  // cannot write one person over the other (lib/db.ts: nothing may be stacked, so nothing is read and written back)
  const person = { email, name, role, classes: [] as string[] };
  const done = await sql`
    update config set value = value || ${sql.json([person])}
    where key = 'app.staff' and not value @> ${sql.json([{ email }])}`;
  if (done.count === 0) redirect("/staff?of=new&refused=already");
  await sendFirstLink(email);
  revalidatePath("/", "layout");
  redirect(`/staff?of=new&saved=${encodeURIComponent(name)}`);
}
