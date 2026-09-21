"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { EngineDown, engineSend } from "@/lib/engine";

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

// A teacher rewords one question. The engine decides: it keeps the numbers — so the answer cannot
// change — saves the new wording as a new question and retires the old one. A refusal comes back
// in the engine's own words and is shown on the question's page; nothing has changed.
export async function correctItem(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const key = String(formData.get("item_key") ?? "");
  if (!/^[A-Za-z0-9._-]+$/.test(key)) redirect("/library");
  let next = `/library/${key}`;
  try {
    const res = await engineSend(`/bank/item/${key}/correct`, {
      stem: String(formData.get("stem") ?? "").slice(0, 600),
      reason: String(formData.get("reason") ?? "").slice(0, 300),
      by: me.email,
    });
    const body = (await res.json()) as { item_key?: string; detail?: unknown };
    next = res.ok
      ? `/library/${body.item_key}?corrected=1`
      : `${next}?error=${encodeURIComponent(typeof body.detail === "string" ? body.detail : "That wording could not be saved. Nothing was changed.")}`;
  } catch (e) {
    next = `${next}?error=${encodeURIComponent(e instanceof EngineDown ? e.message : "The engine could not be reached. Nothing was changed.")}`;
  }
  revalidatePath("/library");
  redirect(next);
}
