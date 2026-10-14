"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";

const CODE = /^[A-Za-z0-9._#-]+$/;

/** A person answers a question the engine drafted, in their own name: agreed as drafted, or corrected in their own
 *  words (goals/ny1-needs-you.yaml). Only a question still waiting is answered, so two people never overwrite each
 *  other; `engine asks` prints the answer for whoever builds next. */
export async function answerAsk(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const code = String(formData.get("code") ?? "");
  const correction = String(formData.get("correction") ?? "").trim();
  const corrected = formData.get("answer") === "corrected";
  if (!CODE.test(code) || (corrected && !correction)) redirect(`/asks${corrected ? "?empty=1" : ""}`);
  // each question is drafted for a role (`ask.for_role`); the coordinator may answer any
  const [ask] = await sql<{ for_role: string }[]>`select for_role from ask where code = ${code}`;
  if (ask && me.role !== "coordinator" && me.role !== ask.for_role) redirect(`/refused?kind=asks&role=${ask.for_role}`);
  await sql`
    update ask set answer = ${corrected ? "corrected" : "agreed"}, correction = ${corrected ? correction : null},
                   answered_by = ${me.name}, answered_at = now()
    where code = ${code} and answer is null`;
  revalidatePath("/asks");
  revalidatePath("/today");
  redirect("/asks");
}
