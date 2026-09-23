"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { EngineDown, engineSend } from "@/lib/engine";

const UUID = /^[0-9a-f-]{36}$/;

/** A person stands behind the machine's marking of this child's papers: every candidate the
 *  marker could settle becomes evidence, and the map is rebuilt from it. */
export async function confirmChild(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  if (!UUID.test(id)) redirect("/growth");
  const [{ n }] = await sql<{ n: number }[]>`select confirm_results(${id}::uuid, ${me.email}) as n`;
  revalidatePath(`/growth/${id}`);
  redirect(`/growth/${id}?confirmed=${n}`);
}

/** A person settles one answer the machine could not read or mark. */
export async function resolveOne(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("result_id") ?? "");
  const child = String(formData.get("child_id") ?? "");
  const status = String(formData.get("status") ?? "");
  if (!UUID.test(id) || !UUID.test(child)) redirect("/growth");
  if (!["correct", "wrong", "blank"].includes(status)) redirect(`/growth/${child}?error=resolve`);
  await sql`select resolve_result(${id}::uuid, ${status}, '{}'::text[], ${me.email})`;
  revalidatePath(`/growth/${child}`);
  redirect(`/growth/${child}?resolved=1`);
}

/** A teacher approves the child's next paper, proposed from their own ladder (goals/s11-focus-paper.yaml,
 *  u2-children.yaml). The engine proposes and prints; this is the approval, in the person's name. */
export async function approveNextPaper(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  const week = String(formData.get("week") ?? "");
  if (!UUID.test(id) || !/^\d{4}-W\d{2}$/.test(week)) redirect("/growth");
  const res = await engineSend(`/child/${id}/focus`, { week, by: me.email });
  revalidatePath(`/growth/${id}`);
  // already approved this week (a second click, or a colleague first): the page shows who approved it
  if (res.status === 409) redirect(`/growth/${id}`);
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}). Nothing was changed.`);
  const made = (await res.json()) as { qr: string };
  redirect(`/growth/${id}?paper=${made.qr}`);
}
