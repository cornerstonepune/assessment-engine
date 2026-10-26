"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding } from "@/lib/decides";
import { EngineDown, engineSend } from "@/lib/engine";
import { levels as schoolLevels } from "@/lib/levels";

// A kind of question stopped at a level, or at every level, or used again (goals/gen_retire_a_kind.yaml), by whoever may
// change the skill. The engine refuses in words (a level keeps one kind in use); what it did comes back to the page:
// the levels that wait for approval again, and the approved papers not yet given that went back for approval.

const CODE = /^[A-Z0-9._]+$/; // a skill's code
const KIND = /^[A-Za-z0-9._]+$/; // a kind's: a template's name, or a printed format's ("bare_sum")

async function where(fd: FormData): Promise<{ code: string; level: string | null; kind: string }> {
  const code = String(fd.get("code") ?? "");
  const level = String(fd.get("level") ?? "");
  const kind = String(fd.get("kind") ?? "");
  if (!CODE.test(code) || !KIND.test(kind) || (level !== "all" && !(await schoolLevels()).order.includes(level))) redirect("/");
  return { code, level: level === "all" ? null : level, kind };
}

type Answer = { stopped?: boolean; started?: boolean; why?: string; levels?: string[]; withdrawn?: string[] };

async function send(path: `/skill/${string}/kind/stop` | `/skill/${string}/kind/start`, body: { level: string | null; kind: string; by: string }) {
  try {
    return (await (await engineSend(path, body)).json()) as Answer;
  } catch (e) {
    return { why: e instanceof EngineDown ? e.message : "The engine could not be reached." } as Answer;
  }
}

function back(code: string, a: Answer, said: string): never {
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  if (!(a.stopped || a.started)) redirect(`/skill-sets/${code}?refused=${encodeURIComponent(a.why || "That could not be done.")}#stop-kinds`);
  const papers = a.withdrawn?.length ? `&withdrawn=${a.withdrawn.join(",")}` : "";
  redirect(`/skill-sets/${code}?changed=${said}&at=${encodeURIComponent((a.levels ?? []).join(", "))}${papers}#stop-kinds`);
}

export async function stopKind(fd: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const { code, level, kind } = await where(fd);
  back(code, await send(`/skill/${code}/kind/stop`, { level, kind, by: me.name }), "kind_stopped");
}

export async function startKind(fd: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const { code, level, kind } = await where(fd);
  back(code, await send(`/skill/${code}/kind/start`, { level, kind, by: me.name }), "kind_started");
}
