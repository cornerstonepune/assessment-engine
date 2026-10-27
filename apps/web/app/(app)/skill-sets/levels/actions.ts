"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { levelRows, recordLookedAt } from "@/lib/queries-calibration";
import { scopeOf } from "@/lib/scope";

const BACK = /^\/skill-sets\/levels(\?[\w=&.%-]*)?$/;

/** "I've looked at this": adds a row saying who looked, and the counts at the time (never a form's own). The suggestion is
 *  hidden for that grade or class until the numbers move; nothing about the level changes. Only a level the person is
 *  shown can be looked at: a form changed by hand for another class is refused. */
export async function lookedAt(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const kind = formData.get("kind") === "grade" ? "grade" : "class";
  const scope = String(formData.get("scope") ?? "");
  const skill = String(formData.get("skill") ?? "");
  const difficulty = String(formData.get("difficulty") ?? "");
  const back = String(formData.get("back") ?? "");
  const shown = (await levelRows(scopeOf(me))).some(
    (r) => r.kind === kind && r.scope === scope && r.skill === skill && r.difficulty === difficulty,
  );
  if (shown) await recordLookedAt(me.email, { kind, scope, skill, difficulty });
  revalidatePath("/skill-sets/levels");
  redirect(BACK.test(back) ? back : "/skill-sets/levels");
}
