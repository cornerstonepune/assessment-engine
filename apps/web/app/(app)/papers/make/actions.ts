"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { childrenSections } from "@/lib/scope";
import { batchQuery, makeBatch, readBatch, UUID } from "@/lib/maker";

const WEEK = /^\d{4}-W\d{2}$/;

/** The papers the educator has just seen, made and approved in their name exactly as seen (goals/m3-the-maker.yaml,
 *  goals/preview-before-print.yaml). The same form
 *  sent twice makes them once (`once`, one per page drawn); a batch the engine refuses comes back with its words, and
 *  one it did not answer on comes back with the same `once`, so sending it again cannot make the papers twice. */
export async function makePapers(formData: FormData): Promise<void> {
  const week = String(formData.get("week") ?? "");
  const once = String(formData.get("once") ?? "");
  const seen = String(formData.get("seen") ?? "");
  const batch = readBatch((k) => formData.getAll(k).map(String), week);
  if (!batch || !batch.children.length || !WEEK.test(week) || !UUID.test(once) || !seen) redirect("/papers/make");
  // a home assessment is the home papers' decision; a class practice or assessment, the class papers'
  const kind = batch.kind === "focus" ? "home_papers" : "class_papers";
  const me = await deciding(kind);
  mustBeMine(me, kind, [batch.section, ...(await childrenSections(batch.children))]);
  const out = await makeBatch(batch, me.email, once, seen);
  if ("why" in out) {
    const q = batchQuery(batch);
    if (out.unsure) q.set("once", once);
    q.set("why", out.why);
    redirect(`/papers/make?${q}`);
  }
  revalidatePath("/papers");
  const q = new URLSearchParams({ class: batch.section, kind: batch.kind, made: out.made.qrs.join(".") });
  if (out.made.already) q.set("already", "1");
  redirect(`/papers/make?${q}`);
}
