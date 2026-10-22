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
