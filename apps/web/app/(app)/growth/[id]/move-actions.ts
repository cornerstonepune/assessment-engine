"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { mayUse } from "@/lib/access";
import { sql } from "@/lib/db";

const UUID = /^[0-9a-f-]{36}$/;

type Said = { moved: boolean; refused?: string; prescriptions_withdrawn?: number; papers_made?: number };

/** A coordinator changes a child's grade, or moves them to another class (goals/mov_move_a_child.yaml). Checked here, on
 *  the server, before anything is written: a form can be changed by hand, so hiding the button is not the check. The rule
 *  itself is the database's (`move_child`): it says why it refused, and a refusal changes nothing. */
export async function moveChild(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  if (!UUID.test(id)) redirect("/growth");
  const back = `/growth/${id}`;
  if (!mayUse(me, "move_child")) redirect(`${back}?refused=not_coordinator#grade-class`);
  const band = String(formData.get("band") ?? "").trim();
  const section = String(formData.get("section") ?? "").trim();
  const roll = String(formData.get("roll") ?? "").trim();
  const reason = String(formData.get("reason") ?? "").trim().slice(0, 500);
  const [{ said }] = await sql<{ said: Said }[]>`
    select move_child(${id}::uuid, ${band}, ${section}, ${roll}, ${me.email}, ${reason}) as said`;
  if (!said.moved) {
    const to = new URLSearchParams({ refused: said.refused ?? "", section, roll });
    redirect(`${back}?${to}#grade-class`);
  }
  revalidatePath("/", "layout");
  const done = new URLSearchParams({ moved: "1", withdrawn: String(said.prescriptions_withdrawn ?? 0), made: String(said.papers_made ?? 0) });
  redirect(`${back}?${done}#grade-class`);
}
