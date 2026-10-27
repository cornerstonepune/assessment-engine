"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustSee } from "@/lib/decides";
import { EngineDown, engineSend } from "@/lib/engine";
import { sql } from "@/lib/db";
import { seesSheet } from "@/lib/reach";

// The educator's word on an assessment's card (goals/s2-the-assessment-card.yaml): "Given on" and its day, and a child
// who was away. Each is kept by the engine as a row of its own (w2_print/given.py); the website writes nothing itself.

/** Back to the card it was said on, and only to a card: the address is rebuilt from its own fields. */
function card(form: FormData, said?: string): string {
  const q = new URLSearchParams();
  for (const k of ["class", "week", "kind", "set"]) {
    const v = String(form.get(k) ?? "");
    if (v) q.set(k, v);
  }
  if (said) q.set("said", said);
  return `/papers/card?${q}`;
}

async function send(form: FormData, go: () => Promise<Response>): Promise<never> {
  let said = "";
  try {
    const res = await go();
    if (!res.ok) said = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "the engine would not take it";
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    said = "the engine is not answering; nothing was kept";
  }
  revalidatePath("/papers");
  redirect(card(form, said.slice(0, 200) || undefined));
}

export async function givenOn(form: FormData): Promise<void> {
  const me = await deciding("papers");
  const on = String(form.get("on") ?? "");
  const qrs = form.getAll("qr").map(String).filter((q) => /^CS[0-9A-F]{6}$/i.test(q));
  // only papers of the classes the card names, and only those the person sees: the engine checks they are papers at all
  const rows = qrs.length ? await sql<{ qr: string }[]>`
    select si.qr_code as qr from sheet_instance si left join child c on c.id = si.child_id
    where si.qr_code = any(${qrs}) and coalesce(si.section, c.section) = ${String(form.get("class") ?? "")}
      and ${seesSheet(me, sql`si.id`)}` : [];
  if (rows.length < qrs.length) redirect("/refused?kind=papers&paper=1");
  await send(form, () => engineSend("/papers/given", { qrs: rows.map((r) => r.qr), on, by: me.email }));
}

export async function away(form: FormData): Promise<void> {
  const me = await deciding("papers");
  const qr = String(form.get("qr") ?? "");
  await mustSee(me, "papers", [{ qr }]);
  await send(form, () => engineSend("/papers/absent", { qr, away: form.get("away") === "yes", by: me.email }));
}
