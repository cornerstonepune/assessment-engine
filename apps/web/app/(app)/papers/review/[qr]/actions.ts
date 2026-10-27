"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { deciding } from "@/lib/decides";
import { sees } from "@/lib/reach";
import { engineSend } from "@/lib/engine";
import type { Session } from "@/lib/auth";

// A child's paper reviewed, a question removed or added, and the paper approved (goals/paper_review_add_remove.yaml).
// The engine holds every rule (`w2_print/edit_paper.py`): what may change, the limits, the new code, the edit's row.

const QR = /^CS[0-9A-F]{6}$/;
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Who may change or approve this paper: whoever the shared rule lets see it (`staff_sees`: a coordinator, the class's
 *  educators, or whoever put the paper's file in; lib/reach.ts, goals/own_who_sees_answers.yaml). Asked on the server of
 *  every action: a link to another class's paper changes nothing. */
async function mayChange(me: Session, qr: string): Promise<void> {
  if (!(await sees(me, [{ qr }]))) redirect("/refused?kind=papers&paper=1");
}

async function said(res: Response): Promise<string> {
  return ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? `The engine answered ${res.status}.`;
}

const back = (qr: string, q: Record<string, string | string[]>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) for (const x of [v].flat()) s.append(k, x);
  return `/papers/review/${qr}?${s}`;
};

/** One question off the paper, or one from the bank onto it. The paper is made again with a new code, so the page
 *  moves to it; a refusal stays on this one and says why. */
export async function changePaper(formData: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const qr = String(formData.get("qr") ?? "");
  const item = String(formData.get("item_id") ?? "");
  const what = formData.get("what") === "add" ? "add" : "remove";
  const at = Number(formData.get("at") ?? "") || null;
  if (!QR.test(qr) || !ID.test(item)) redirect("/papers");
  await mayChange(me, qr);
  const res = await engineSend(`/paper/${qr}/${what}`, { by: me.email, item_id: item, at });
  if (!res.ok) redirect(back(qr, { error: await said(res) }));
  const out = (await res.json()) as { qr: string; n: number; withdrew_approval: boolean; uncovered: string[] };
  revalidatePath("/papers");
  redirect(back(out.qr, { done: what, n: String(out.n), ...(out.withdrew_approval ? { withdrew: "1" } : {}), gone: out.uncovered }));
}

/** The paper approved in the educator's name: from now on it may be printed. */
export async function approvePaper(formData: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const qr = String(formData.get("qr") ?? "");
  if (!QR.test(qr)) redirect("/papers");
  await mayChange(me, qr);
  const res = await engineSend(`/paper/${qr}/approve`, { by: me.email });
  revalidatePath("/papers");
  redirect(back(qr, res.ok ? { done: "approved" } : { error: await said(res) }));
}
