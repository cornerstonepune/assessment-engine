"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { sql } from "@/lib/db";

const CODE = /^[A-Z0-9_]+$/;
const SKILL = /^[A-Z0-9_.]+$/;

/** A person says a class has been taught a topic, or not yet, in their own name (goals/f1f-taught-per-class.yaml): an
 *  educator for their own classes, the coordinator for any. Said of a topic, it is said of every skill in it; with a
 *  `skill`, of that one skill alone, so a class can be taught Multiplication and not yet its columns
 *  (goals/t1-topics-are-operations.yaml). From then on that class reads its own word, never the school's; no other
 *  class changes. Taught, a skill is on the class's pages and can go on its children's papers; not taught, it is kept
 *  out of its sight. A class no child is in is no class: nothing is said (`say_taught`). */
export async function switchTopic(formData: FormData): Promise<void> {
  const me = await deciding("topics");
  const code = String(formData.get("code") ?? "");
  const skill = String(formData.get("skill") ?? "") || null;
  const section = String(formData.get("class") ?? "");
  const on = formData.get("taught") === "on";
  if (!CODE.test(code) || !section || (skill && !SKILL.test(skill))) redirect("/");
  mustBeMine(me, "topics", [section]);
  const rows = await sql<{ n: number }[]>`
    select say_taught(t.tenant_id, ${section}, t.code, ${skill}, ${on}, ${me.name}) as n from topic t where t.code = ${code}`;
  const n = rows[0]?.n ?? 0;
  // every page reads what is taught: Curriculum, Today, the Question bank, the papers
  revalidatePath("/", "layout");
  const said = new URLSearchParams({ [on ? "on" : "off"]: skill ?? code, class: section });
  redirect(n ? `/?${said}#${on ? "taught" : "not-taught"}` : "/");
}
