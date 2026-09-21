"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";

// Any staff member, any question, one line of reason. The engine retires it and, in the same
// transaction, the worksheets it was on — dealing new ones — so no worksheet ever holds a question
// that has left the bank (ADR 0026). If the engine cannot be reached, nothing has changed.
export async function flagItem(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const itemKey = String(formData.get("item_key") ?? "");
  const note = String(formData.get("note") ?? "").trim().slice(0, 300);
  const back = String(formData.get("back") ?? "/library");
  if (!/^[A-Za-z0-9._-]+$/.test(itemKey) || !/^\/library(\/|\?|$)/.test(back)) redirect("/library");
  let next = back;
  try {
    const res = await engineSend(`/bank/item/${itemKey}/remove`, { by: me.email, note });
    if (!res.ok) next = `/library/${itemKey}?error=${encodeURIComponent("That question could not be removed. Nothing was changed.")}`;
  } catch (e) {
    next = `/library/${itemKey}?error=${encodeURIComponent(e instanceof EngineDown ? e.message : "The engine could not be reached. Nothing was changed.")}`;
  }
  revalidatePath("/library");
  revalidatePath("/worksheets");
  revalidatePath("/");
  redirect(next);
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
