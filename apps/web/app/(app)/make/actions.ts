"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { childSection, childrenSections } from "@/lib/scope";
import { customHref, makePaper, readArea, readDraw, type Area } from "@/lib/next-paper";

const UUID = /^[0-9a-f-]{36}$/;
const WEEK = /^\d{4}-W\d{2}$/;

/** One child's home paper, or every one proposed in the class at once — each in the teacher's name, each the questions
 *  the teacher saw (`draw`, `seen`, one per child in the same order). A child whose questions changed since is not
 *  printed; the page shows theirs again. */
export async function approveHome(formData: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const week = String(formData.get("week") ?? "");
  const section = String(formData.get("section") ?? "");
  const ids = formData.getAll("child_id").map(String);
  const draws = formData.getAll("draw").map(String);
  const seen = formData.getAll("seen").map(String);
  const back = `/make/${encodeURIComponent(section)}`;
  if (!WEEK.test(week) || !ids.every((id) => UUID.test(id)) || seen.length !== ids.length || seen.some((s) => !s)) redirect(back);
  await mustBeMine(me, "home_papers", [section, ...(await childrenSections(ids))]);
  const q = new URLSearchParams();
  let made = 0;
  let changed = 0;
  for (const [i, id] of ids.entries()) {
    const draw = readDraw(draws[i]);
    const out = await makePaper(id, week, me.email, { draw, seen: seen[i] });
    if (out.qr) made += 1;
    if (out.changed) {
      changed += 1;
      if (draw) q.append("draw", `${id}~${draw}`);
    }
  }
  revalidatePath("/make");
  q.set("approved", String(made));
  if (changed) q.set("changed", String(changed));
  redirect(`${back}?${q}`);
}

/** The paper a teacher chose for one child, approved in their name exactly as they saw it; it opens on its review page,
 *  its questions to remove or add (goals/paper_review_add_remove.yaml). */
export async function approveCustom(formData: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const child = String(formData.get("child") ?? "");
  const week = String(formData.get("week") ?? "");
  const areas = formData.getAll("a").map(String).map(readArea).filter((a): a is Area => !!a);
  const draw = readDraw(String(formData.get("draw") ?? ""));
  const seen = String(formData.get("seen") ?? "");
  if (!UUID.test(child) || !WEEK.test(week) || !areas.length || !seen) redirect("/make");
  await mustBeMine(me, "home_papers", [await childSection(child)]);
  const { qr, changed } = await makePaper(child, week, me.email, { draw, seen }, areas);
  revalidatePath("/make");
  if (changed) redirect(`${customHref(child, areas, draw)}&changed=1`);
  redirect(`/papers/review/${qr}`);
}
