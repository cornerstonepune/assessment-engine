"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { mustBeOn, slipsMax } from "@/lib/curriculum-screens";
import { PART_KEYS } from "@/lib/page-part";
import { enginePost } from "@/lib/engine";

// Every answer is the engine's, made as the signed-in member of staff; the page then goes where `back` says. `back` is
// one of this site's own addresses and nothing else.
const own = (back: FormDataEntryValue | null) => (typeof back === "string" && /^\/curriculum\/[\w/?=&.%-]*$/.test(back) ? back : "/curriculum/fill");
const field = (f: FormData, k: string) => String(f.get(k) ?? "");

function target(form: FormData) {
  const [code, part, back] = [field(form, "code"), field(form, "part"), own(form.get("back"))];
  if (!(PART_KEYS as readonly string[]).includes(part)) throw new Error("not a part of a page");
  return { code, part, back };
}
function done(back: string): never {
  revalidatePath("/curriculum", "layout");
  redirect(back);
}

/** Keep a drafted part as written, or send it back (the part is emptied). */
export async function answerPart(form: FormData): Promise<void> {
  const me = await requireStaff();
  await mustBeOn(me.email);
  const { code, part, back } = target(form);
  await enginePost(form.get("do") === "keep" ? "/curriculum/page/confirm" : "/curriculum/page/revert", { actor: me.email, code, part });
  done(back);
}

/** A person's own words in place of the draft: lines for the steps, an idea and slips for the thinking, else text. */
export async function editPart(form: FormData): Promise<void> {
  const me = await requireStaff();
  await mustBeOn(me.email);
  const { code, part, back } = target(form);
  const lines = field(form, "words").split("\n").map((l) => l.trim()).filter(Boolean);
  const slips = Array.from({ length: await slipsMax() }, (_, i) => i).map((i) => ({ keyword: field(form, `keyword${i}`).trim(), spot: field(form, `spot${i}`).trim() })).filter((s) => s.keyword && s.spot);
  const base = { actor: me.email, code, part };
  if (part === "steps") await enginePost("/curriculum/page/edit", { ...base, items: lines });
  else if (part === "thinking") await enginePost("/curriculum/page/edit", { ...base, idea: field(form, "idea").trim(), slips });
  else await enginePost("/curriculum/page/edit", { ...base, text: field(form, "words").trim() });
  done(back);
}

/** Yes adds the offered skills as links; no closes the offer. */
export async function answerOffer(form: FormData): Promise<void> {
  const me = await requireStaff();
  await mustBeOn(me.email);
  await enginePost("/curriculum/offers/answer", { actor: me.email, id: field(form, "id"), yes: form.get("do") === "yes" });
  revalidatePath("/curriculum/offers");
  redirect("/curriculum/offers");
}
