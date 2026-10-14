"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { childSection, childrenSections } from "@/lib/scope";
import { makePaper, readArea, type Area } from "@/lib/next-paper";

const UUID = /^[0-9a-f-]{36}$/;
const WEEK = /^\d{4}-W\d{2}$/;

/** One child's home paper, or every one proposed in the class at once — each in the teacher's name. */
export async function approveHome(formData: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const week = String(formData.get("week") ?? "");
  const section = String(formData.get("section") ?? "");
  const ids = formData.getAll("child_id").map(String);
  const back = `/make/${encodeURIComponent(section)}`;
  if (!WEEK.test(week) || !ids.every((id) => UUID.test(id))) redirect(back);
  mustBeMine(me, "home_papers", [section, ...(await childrenSections(ids))]);
  let made = 0;
  for (const id of ids) if (await makePaper(id, week, me.email)) made += 1;
  revalidatePath("/make");
  redirect(`${back}?approved=${made}`);
}

/** The paper a teacher chose for one child, printed in their name; it opens as printed. */
export async function approveCustom(formData: FormData): Promise<void> {
  const me = await deciding("home_papers");
  const child = String(formData.get("child") ?? "");
  const week = String(formData.get("week") ?? "");
  const areas = formData.getAll("a").map(String).map(readArea).filter((a): a is Area => !!a);
  if (!UUID.test(child) || !WEEK.test(week) || !areas.length) redirect("/make");
  mustBeMine(me, "home_papers", [await childSection(child)]);
  const qr = await makePaper(child, week, me.email, areas);
  revalidatePath("/make");
  redirect(`/worksheets/${qr}`);
}
