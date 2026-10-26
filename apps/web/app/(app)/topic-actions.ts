"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
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
  await sql`
    select say_taught(t.tenant_id, ${section}, t.code, ${skill}, ${on}, ${me.name}) as n from topic t where t.code = ${code}`;
  // every page reads what is taught: Curriculum, What needs doing, the Question bank, the papers
  revalidatePath("/", "layout");
  // back to the page it was said on (What needs doing, or a Curriculum row); only a path of this site is followed
  const from = (await headers()).get("referer");
  const back = from ? new URL(from).pathname + new URL(from).search : "/today";
  const to = new URL(back.startsWith("/") && !back.startsWith("//") ? back : "/today", "http://site");
  // it comes back saying what was said, on the page it was said on (`TaughtNotice`)
  to.searchParams.set("said", skill ?? code);
  to.searchParams.set("in", section);
  to.searchParams.set("taught", on ? "1" : "0");
  redirect(to.pathname + to.search);
}
