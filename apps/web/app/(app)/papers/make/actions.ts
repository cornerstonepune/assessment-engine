"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { engineSend } from "@/lib/engine";
import { batchQuery, readBatch } from "@/lib/maker";

const ONCE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const WEEK = /^\d{4}-W\d{2}$/;

/** The papers the educator has just seen, made and approved in their name (goals/m3-the-maker.yaml). The same form
 *  sent twice makes them once (`once`, one per page drawn); a batch the engine refuses comes back with its words. */
export async function makePapers(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const week = String(formData.get("week") ?? "");
  const once = String(formData.get("once") ?? "");
  const batch = readBatch((k) => formData.getAll(k).map(String), week);
  if (!batch || !batch.children.length || !WEEK.test(week) || !ONCE.test(once)) redirect("/papers/make");
  const res = await engineSend("/papers/make", { ...batch, by: me.email, once });
  if (!res.ok) {
    const detail = ((await res.json().catch(() => ({}))) as { detail?: unknown }).detail;
    const why = typeof detail === "string" ? detail : `The engine refused (${res.status}); nothing was printed.`;
    redirect(`/papers/make?${batchQuery(batch)}&why=${encodeURIComponent(why)}`);
  }
  const made = (await res.json()) as { qrs: string[]; already: boolean };
  revalidatePath("/papers");
  const q = new URLSearchParams({ class: batch.section, kind: batch.kind, made: made.qrs.join(".") });
  if (made.already) q.set("already", "1");
  redirect(`/papers/make?${q}`);
}
