"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";

// Any staff member, any item, one line of reason. The database trigger retires the item.
export async function flagItem(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const itemKey = String(formData.get("item_key") ?? "");
  const note = String(formData.get("note") ?? "").trim().slice(0, 300);
  const back = String(formData.get("back") ?? "/library");
  if (!/^[A-Za-z0-9._-]+$/.test(itemKey) || !back.startsWith("/library")) redirect("/library");

  const rows = await sql<{ id: string; tenant_id: string }[]>`select id, tenant_id from item where item_key = ${itemKey}`;
  if (rows.length === 0) redirect(back);
  await sql`insert into item_feedback (tenant_id, item_id, actor, verdict, note)
            values (${rows[0].tenant_id}, ${rows[0].id}, ${me.email}, 'retire', ${note})`;
  revalidatePath("/library");
  revalidatePath("/");
  redirect(back);
}
