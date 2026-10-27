"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { sql, TENANT_SLUG } from "@/lib/db";
import { EngineDown, engineSend } from "@/lib/engine";
import { requireStaff } from "@/lib/auth";

// What an educator says about an assessment from its row (goals/asm_assessments_page.yaml): the name she gives it, and,
// for a home assessment, the approval of that one row's papers. Never all rows at once.

const KEY = /^(practice|assessment|focus|custom|earlier)~[^~]{0,60}~[^~]{0,20}~.{0,2000}$/;
const WEEK = /^\d{4}-W\d{2}$/;

/** Back to the list, and only to the list. */
const back = (f: FormData, said?: string) => {
  const q = new URLSearchParams(String(f.get("back") ?? "").replace(/^\/papers\??/, ""));
  q.delete("said");
  if (said) q.set("said", said);
  const s = q.toString();
  return s ? `/papers?${s}` : "/papers";
};

/** A new row for the assessment's name; the older names stay (rule 4). An empty name changes nothing. */
export async function renameAssessment(f: FormData): Promise<void> {
  const me = await requireStaff();
  const key = String(f.get("key") ?? "");
  const name = String(f.get("name") ?? "").trim().slice(0, 120);
  if (!KEY.test(key)) redirect(back(f));
  if (name) {
    await sql`
      insert into assessment_name (tenant_id, key, name, named_by)
      select id, ${key}, ${name}, ${me.email} from tenant where slug = ${TENANT_SLUG}`;
  }
  revalidatePath("/papers");
  redirect(back(f));
}

/** One row's approval: the engine approves that class's home assessments for that week in the educator's name, the one
 *  approval the print flow uses. Not all rows: a row at a time. */
export async function approveRow(f: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const section = String(f.get("section") ?? "");
  const week = String(f.get("week") ?? "");
  if (!section || !WEEK.test(week)) redirect(back(f));
  await mustBeMine(me, "home_papers", [section]);
  let said: string | undefined;
  try {
    const res = await engineSend("/week/approve", { section, week, kind: "focus", by: me.email });
    if (!res.ok) said = `The engine refused that (${res.status}). Nothing was approved.`;
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    said = "The engine is not answering; nothing was approved.";
  }
  revalidatePath("/papers");
  redirect(back(f, said));
}
