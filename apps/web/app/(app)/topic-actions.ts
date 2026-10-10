"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";

const CODE = /^[A-Z0-9_]+$/;

/** A person says a topic is taught, or not yet, in their own name (goals/ny1-needs-you.yaml). From then on the rows
 *  never switch it back (`engine/core/topics.py`): switched on, its skills are on Curriculum, the Question bank and
 *  children's papers; switched off, they keep their questions out of sight. */
export async function switchTopic(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const code = String(formData.get("code") ?? "");
  const on = formData.get("taught") === "on";
  if (!CODE.test(code)) redirect("/");
  const [t] = await sql<{ code: string }[]>`
    update topic set taught = ${on}, taught_by = ${me.name}, taught_at = now() where code = ${code} returning code`;
  // every page reads what is taught: Curriculum, Today, the Question bank, the papers
  revalidatePath("/", "layout");
  redirect(t ? `/?${on ? "on" : "off"}=${encodeURIComponent(code)}#${on ? "taught" : "not-taught"}` : "/");
}
