"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding } from "@/lib/decides";
import { type BodyOf, EngineDown, engineSend, type PostPath } from "@/lib/engine";
import { levels as schoolLevels } from "@/lib/levels";
import { NEW_PASSAGE } from "./sample-shape";

// An educator changes an English skill's samples, or the kinds a level asks (goals/edt_edit_samples_and_kinds.yaml).
// Nimish, 2026-10-24: "It should simply have the capability to edit the skill, where the nature or the description of
// the skill can be changed." The engine checks every sample by code before it stores it and says in words what failed;
// a refused save comes back to the form with those words beside their fields and what was typed kept. A save withdraws
// that level's approval and keeps what it replaced (the engine's `english_sample_edit`).

const CODE = /^[A-Z0-9._]+$/; // a skill's code, and a kind's
const FIELDS = ["ask", "text", "options", "left", "right", "answer", "accept", "key_points", "not_words"] as const;

/** What a form sent back: the faults by field, in words; for a kind added with its samples, one set per sample. */
export type SampleState = {
  faults: Record<string, string[]>;
  samples?: Record<string, string[]>[];
  why?: string;
  /** what the form sent, so a refused form shows what was typed */
  sent?: Record<string, string[]>;
};

function sentOf(fd: FormData): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [k, v] of fd.entries()) if (typeof v === "string" && !k.startsWith("$")) (out[k] ??= []).push(v);
  return out;
}

type Form = BodyOf<"/skill/X/sample">;
type One = Pick<Form, "fields" | "wrong" | "passage_code" | "passage_title" | "passage_text" | "rubric_code">;

/** One sample as its form sent it, the names under `p` (a kind's three samples are p = "s0.", "s1.", "s2."). */
function sampleOf(fd: FormData, p = ""): One {
  const text = (name: string, max = 4000) => String(fd.get(p + name) ?? "").slice(0, max);
  const answers = fd.getAll(`${p}wrong_answer`).map(String);
  const mistakes = fd.getAll(`${p}wrong_mistake`).map(String);
  const passage = text("passage", 80);
  return {
    fields: Object.fromEntries(FIELDS.map((f) => [f, text(f)])) as One["fields"],
    wrong: answers.map((answer, i) => ({ answer: answer.slice(0, 600), mistake_code: (mistakes[i] ?? "").slice(0, 80) })),
    passage_code: passage && passage !== NEW_PASSAGE ? passage : null,
    passage_title: passage === NEW_PASSAGE ? text("passage_title", 200) : null,
    passage_text: passage === NEW_PASSAGE ? text("passage_text", 8000) : null,
    rubric_code: text("rubric", 80) || null,
  };
}

async function where(fd: FormData): Promise<{ code: string; level: string; kind: string }> {
  const code = String(fd.get("code") ?? "");
  const level = String(fd.get("level") ?? "");
  const kind = String(fd.get("kind") ?? "");
  if (!CODE.test(code) || !CODE.test(kind) || !(await schoolLevels()).order.includes(level)) redirect("/");
  return { code, level, kind };
}

function done(code: string, level: string, said: string): never {
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  redirect(`/skill-sets/${code}?changed=${encodeURIComponent(said)}&at=${level}#level-${level}`);
}

const unreachable = (e: unknown, fd: FormData): SampleState => ({
  faults: { skill: [e instanceof EngineDown ? e.message : "The engine could not be reached. Nothing was saved."] },
  sent: sentOf(fd),
});

/** One sample changed (it names its number) or added (it names none). */
export async function saveSample(_: SampleState, fd: FormData): Promise<SampleState> {
  const me = await deciding("skill_drafts");
  const { code, level, kind } = await where(fd);
  const ord = Number(fd.get("ord")) || null;
  try {
    const res = await engineSend(`/skill/${code}/sample`, { level, kind, ord, by: me.name, ...sampleOf(fd) });
    const body = (await res.json()) as { saved?: boolean; faults?: Record<string, string[]> };
    if (!res.ok || !body.saved)
      return { faults: body.faults ?? { skill: ["That sample could not be saved. Nothing was changed."] }, sent: sentOf(fd) };
  } catch (e) {
    return unreachable(e, fd);
  }
  done(code, level, ord ? "sample" : "added");
}

/** A removal the engine answers {removed, why}: back to the level, saying it was done or why it was not. */
async function taking<P extends PostPath>(
  code: string, level: string, path: P, body: BodyOf<P>, said: string,
): Promise<never> {
  let why = "";
  try {
    const res = await engineSend(path, body);
    const answer = (await res.json()) as { removed?: boolean; why?: string };
    why = answer.removed ? "" : (answer.why ?? "That could not be taken off.");
  } catch (e) {
    why = e instanceof EngineDown ? e.message : "The engine could not be reached. Nothing was changed.";
  }
  if (why) redirect(`/skill-sets/${code}?refused=${encodeURIComponent(why)}&at=${level}#level-${level}`);
  done(code, level, said);
}

/** One sample taken off its level; a level keeps three of each kind. */
export async function removeSample(fd: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const { code, level, kind } = await where(fd);
  const ord = Number(fd.get("ord"));
  if (!Number.isInteger(ord) || ord < 1) redirect("/");
  await taking(code, level, `/skill/${code}/sample/remove`, { level, kind, ord, by: me.name }, "removed");
}

/** A kind added to a level, with the three samples it needs; each is checked. */
export async function addKind(_: SampleState, fd: FormData): Promise<SampleState> {
  const me = await deciding("skill_drafts");
  const { code, level, kind } = await where(fd);
  const n = Math.min(Number(fd.get("samples")) || 0, 6);
  const samples = Array.from({ length: n }, (_, i) => sampleOf(fd, `s${i}.`));
  try {
    const res = await engineSend(`/skill/${code}/kind`, { level, kind, samples, by: me.name });
    const body = (await res.json()) as { saved?: boolean; why?: string; faults?: Record<string, string[]>[] };
    if (!res.ok || !body.saved)
      return { faults: {}, why: body.why ?? "That kind could not be added.", samples: body.faults ?? [], sent: sentOf(fd) };
  } catch (e) {
    return unreachable(e, fd);
  }
  done(code, level, "kind_added");
}

/** A kind taken from a level; a level asks at least one. */
export async function removeKind(fd: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const { code, level, kind } = await where(fd);
  await taking(code, level, `/skill/${code}/kind/remove`, { level, kind, by: me.name }, "kind_removed");
}
