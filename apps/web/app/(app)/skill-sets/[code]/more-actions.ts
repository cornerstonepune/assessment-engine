"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding } from "@/lib/decides";
import { EngineDown, engineSend } from "@/lib/engine";
import { levels as schoolLevels } from "@/lib/levels";

// More questions like a sample (goals/gen_from_a_sample.yaml), by whoever may change the skill. The engine makes and
// checks them; what it did comes back to the page in words: how many were made, how many thrown away and why.

const CODE = /^[A-Z0-9._]+$/;

type Answer = { made?: boolean; why?: string; returned?: number; kept?: number; thrown?: { why: string; n: number }[] };

async function where(fd: FormData): Promise<{ code: string; level: string; n: number }> {
  const code = String(fd.get("code") ?? "");
  const level = String(fd.get("level") ?? "");
  const n = Number(fd.get("n"));
  if (!CODE.test(code) || !(await schoolLevels()).order.includes(level) || !Number.isInteger(n)) redirect("/");
  return { code, level, n };
}

async function asking(path: Parameters<typeof engineSend>[0], body: Parameters<typeof engineSend>[1]): Promise<Answer> {
  try {
    return (await (await engineSend(path, body)).json()) as Answer;
  } catch (e) {
    return { why: e instanceof EngineDown ? e.message : "The engine could not be reached." };
  }
}

function back(code: string, level: string, n: number, a: Answer): never {
  revalidatePath(`/skill-sets/${code}`);
  if (!a.made) redirect(`/skill-sets/${code}?refused=${encodeURIComponent(a.why || "No question was made.")}&at=${level}#level-${level}`);
  const said = new URLSearchParams({ made: String(a.kept ?? 0), asked: String(n), at: level });
  if (a.returned !== undefined) said.set("returned", String(a.returned));
  if (a.thrown?.length) said.set("thrown", a.thrown.map((t) => `${t.n}× ${t.why}`).join(" · "));
  redirect(`/skill-sets/${code}?${said}#level-${level}`);
}

export async function moreEnglish(fd: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const { code, level, n } = await where(fd);
  const kind = String(fd.get("kind") ?? "");
  const ord = Number(fd.get("ord"));
  if (!CODE.test(kind) || !Number.isInteger(ord) || ord < 1) redirect("/");
  back(code, level, n, await asking(`/skill/${code}/sample/more`, { level, kind, ord, n, by: me.name }));
}

export async function moreMaths(fd: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const { code, level, n } = await where(fd);
  const text = String(fd.get("text") ?? "").slice(0, 40);
  const layout = fd.get("layout") === "columns" ? "columns" : "line";
  back(code, level, n, await asking(`/skill/${code}/maths/more`, { level, text, layout, n, by: me.name }));
}
