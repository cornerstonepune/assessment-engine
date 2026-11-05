"use server";

import { revalidatePath } from "next/cache";
import { requireStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";

// Her changes to a materials list and the coordinator's answers to a waiting note (M1-10, M1-16): every one is the
// engine's, kept with who made it; the page is drawn again after. No send here (D-076: no WhatsApp screen yet).
const s = (f: FormData, k: string) => String(f.get(k) ?? "").trim();

async function done(res: Promise<Response>, path: string) {
  const got = await res;
  if (!got.ok && got.status !== 409 && got.status !== 422) throw new EngineDown(`The engine refused that (${got.status}).`);
  revalidatePath(path);
}

export async function setQuantity(f: FormData) {
  const me = await requireStaff();
  const q = s(f, "quantity");
  await done(engineSend("/materials/line/quantity", { actor: me.email, line_id: s(f, "line"), quantity: q === "" ? null : Number(q) }), "/educator/materials");
}

export async function removeLine(f: FormData) {
  const me = await requireStaff();
  await done(engineSend("/materials/line/remove", { actor: me.email, line_id: s(f, "line") }), "/educator/materials");
}

export async function addLine(f: FormData) {
  const me = await requireStaff();
  if (!s(f, "code")) return;
  await done(engineSend("/materials/line/add", { actor: me.email, list_id: s(f, "list"), material_code: s(f, "code"), needed_on: s(f, "day") }), "/educator/materials");
}

export async function putOnList(f: FormData) {
  const me = await requireStaff();
  await done(
    engineSend("/materials/review/resolve", { actor: me.email, note_id: s(f, "note"), material_code: s(f, "code"), quantity: Number(s(f, "quantity") || "1"), needed_on: s(f, "day") }),
    "/educator/materials/review",
  );
}

export async function setAside(f: FormData) {
  const me = await requireStaff();
  await done(engineSend("/materials/review/dismiss", { actor: me.email, note_id: s(f, "note"), why: s(f, "why") }), "/educator/materials/review");
}
