"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
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

/** One tap for the whole class: the pack is approved and the sheets are marked printed. */
export async function approvePack(formData: FormData): Promise<void> {
  await requireStaff();
  const section = String(formData.get("section") ?? "");
  const week = String(formData.get("week") ?? "");
  const kind = String(formData.get("kind") ?? "practice");
  const back = BACK(formData);

  await sql`
    update sheet_instance set print_status = 'printed', printed_at = now()
    where print_status = 'new' and sheet_template_id in (
      select st.id from sheet_template st
      left join child c on c.id = st.child_id
      where st.week = ${week}
        and (c.section = ${section} or st.child_id is null)
    ) and id in (
      select si.id from sheet_instance si
      left join prescription p on p.sheet_instance_id = si.id
      where p.kind = ${kind} or p.id is null
    )`;
  revalidatePath("/worksheets");
  redirect(`${back}&approved=1`);
}
