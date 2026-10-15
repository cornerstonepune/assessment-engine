"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { sql } from "@/lib/db";

const CODE = /^[A-Z0-9_]+$/;

/** A person says a class has been taught a topic, or not yet, in their own name (goals/f1f-taught-per-class.yaml): an
 *  educator for their own classes, the coordinator for any. From then on that class reads its own word, never the
 *  school's switch; no other class changes. Taught, the topic's skills are on the class's pages and can go on its
 *  children's papers; not taught, they are kept out of its sight. A class no child is in is no class: nothing is said. */
export async function switchTopic(formData: FormData): Promise<void> {
  const me = await deciding("topics");
  const code = String(formData.get("code") ?? "");
  const section = String(formData.get("class") ?? "");
  const on = formData.get("taught") === "on";
  if (!CODE.test(code) || !section) redirect("/");
  mustBeMine(me, "topics", [section]);
  const [t] = await sql<{ code: string }[]>`
    insert into class_topic (tenant_id, section, topic_code, taught, taught_by, taught_at)
    select t.tenant_id, ${section}, t.code, ${on}, ${me.name}, now() from topic t
    where t.code = ${code}
      and exists (select 1 from child c where c.tenant_id = t.tenant_id and c.section = ${section} and c.active)
    on conflict (tenant_id, section, topic_code)
    do update set taught = excluded.taught, taught_by = excluded.taught_by, taught_at = excluded.taught_at
    returning topic_code as code`;
  // every page reads what is taught: Curriculum, Today, the Question bank, the papers
  revalidatePath("/", "layout");
  const said = new URLSearchParams({ [on ? "on" : "off"]: code, class: section });
  redirect(t ? `/?${said}#${on ? "taught" : "not-taught"}` : "/");
}
