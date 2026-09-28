"use server";

import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";

// The educator confirms their week (N4): the ticked skill sets, their note and what the engine had proposed are kept
// in their name; the latest declaration for a week stands. A refusal comes back in the engine's words.
export async function confirmWeek(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const section = String(formData.get("section") ?? "");
  const week = String(formData.get("week") ?? "");
  const note = String(formData.get("note") ?? "").slice(0, 2000);
  const skillSets = formData.getAll("skill_set").map(String);
  let proposed: unknown[] = [];
  try {
    proposed = JSON.parse(String(formData.get("proposed") ?? "[]")) as unknown[];
  } catch {
    proposed = [];
  }
  const back = `/make/${encodeURIComponent(section)}/week`;
  if (!skillSets.length) redirect(`${back}?error=${encodeURIComponent("Tick at least one skill the class worked on.")}`);
  let next = `${back}?confirmed=1`;
  try {
    const res = await engineSend("/week/declaration", { section, week, note, skill_sets: skillSets, by: me.email, proposed });
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "it could not be kept";
      next = `${back}?error=${encodeURIComponent(`Nothing was kept: ${why}.`)}`;
    }
  } catch (e) {
    next = `${back}?error=${encodeURIComponent(e instanceof EngineDown ? e.message : "The engine could not be reached. Nothing was kept.")}`;
  }
  redirect(next);
}
