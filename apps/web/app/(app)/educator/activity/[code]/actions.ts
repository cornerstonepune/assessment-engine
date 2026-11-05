"use server";

import { revalidatePath } from "next/cache";
import { requireStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";

// Her answers to a drafted part (M1-12b's routes): keep it as it is, put her own words in its place, or send it back.
// The engine refuses the school's own words; the page is drawn again from what it then says.
const part = (f: FormData) => ({ code: String(f.get("code") ?? ""), part: String(f.get("part") ?? "") });

type Me = Awaited<ReturnType<typeof requireStaff>>;

async function answer(me: Me, path: "/curriculum/page/confirm" | "/curriculum/page/revert" | "/curriculum/page/edit", body: Record<string, unknown>, code: string) {
  const res = await engineSend(path, { actor: me.email, ...body } as never);
  if (!res.ok && res.status !== 409) throw new EngineDown(`The engine refused that (${res.status}).`);
  revalidatePath(`/educator/activity/${code}`);
}

export async function keep(f: FormData): Promise<void> {
  const me = await requireStaff();
  const p = part(f);
  await answer(me, "/curriculum/page/confirm", p, p.code);
}

export async function sendBack(f: FormData): Promise<void> {
  const me = await requireStaff();
  const p = part(f);
  await answer(me, "/curriculum/page/revert", p, p.code);
}

/** Her own words: the steps one a line; how to think as an idea line and slips, each "keyword: how to see it". */
export async function edit(f: FormData): Promise<void> {
  const me = await requireStaff();
  const p = part(f);
  const lines = (k: string) => String(f.get(k) ?? "").split("\n").map((l) => l.trim()).filter(Boolean);
  const kind = String(f.get("kind") ?? "text");
  const words =
    kind === "bullets"
      ? { items: lines("items") }
      : kind === "thinking"
        ? {
            idea: String(f.get("idea") ?? "").trim(),
            slips: lines("slips").map((l) => {
              const cut = l.indexOf(":");
              return cut > 0 ? { keyword: l.slice(0, cut).trim(), spot: l.slice(cut + 1).trim() } : { keyword: l, spot: "" };
            }),
          }
        : { text: String(f.get("text") ?? "").trim() };
  await answer(me, "/curriculum/page/edit", { ...p, ...words }, p.code);
}
