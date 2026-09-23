"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { enginePost } from "@/lib/engine";

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

/** Print the child's next paper, chosen from their own ladder (goals/s11-focus-paper.yaml). The engine
 *  chooses and prints; this asks, in the person's name, and shows the paper it made. */
export async function makeFocusPaper(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  const week = String(formData.get("week") ?? "");
  if (!UUID.test(id) || !/^\d{4}-W\d{2}$/.test(week)) redirect("/growth");
  const made = await enginePost<{ qr: string }>(`/child/${id}/focus`, { week, by: me.email });
  revalidatePath(`/growth/${id}`);
  redirect(`/growth/${id}?paper=${made.qr}`);
}
