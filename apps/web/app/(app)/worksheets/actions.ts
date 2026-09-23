"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { EngineDown, engineSend } from "@/lib/engine";
import { DIFFICULTIES } from "@/lib/queries";

const BACK = (f: FormData) => {
  const back = String(f.get("back") ?? "/worksheets");
  return back.startsWith("/worksheets") ? back : "/worksheets";
};

/** The teacher changes one child's level. A reason is required and is kept — the prescriber
 *  reads the override and leaves that child alone next time. */
export async function overrideChild(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("prescription_id") ?? "");
  const difficulty = String(formData.get("difficulty") ?? "");
  const reason = String(formData.get("reason") ?? "").trim().slice(0, 300);
  const back = BACK(formData);
  if (!/^[0-9a-f-]{36}$/.test(id)) redirect(back);
  if (!DIFFICULTIES.includes(difficulty as never) || !reason) redirect(`${back}&error=override`);

  await sql`
    update prescription set difficulty = ${difficulty}, rule_fired = 'override',
      override_by = ${me.email}, override_reason = ${reason}, updated_at = now()
    where id = ${id}::uuid`;
  revalidatePath("/worksheets");
  redirect(`${back}&changed=1`);
}

/** One tap for the whole class: the engine approves the pack in the teacher's name (`w2_print/pack.py`), the one
 *  approval the print flow uses too. The page once repeated it in its own SQL, which found papers through their
 *  template's week — a library worksheet has none, so the tap approved nothing. */
export async function approvePack(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const section = String(formData.get("section") ?? "");
  const week = String(formData.get("week") ?? "");
  const kind = String(formData.get("kind") ?? "practice");
  const back = BACK(formData);
  const res = await engineSend("/week/approve", { section, week, kind, by: me.email });
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}). Nothing was approved.`);
  revalidatePath("/worksheets");
  redirect(`${back}&approved=1`);
}
