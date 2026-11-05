"use server";

import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";
import { refusal } from "@/lib/timetable-rules";

// The rules page's writes (task M1-14 part a): one form, one engine call (`/timetable/rules/change`), the person's
// email as `actor`. Nothing is decided here: a refusal comes back in the engine's own words, on the page.

const text = (f: FormData, k: string) => {
  const v = f.get(k);
  return typeof v === "string" && v.trim() !== "" ? v.trim() : null;
};
const num = (f: FormData, k: string) => {
  const v = text(f, k);
  return v === null || Number.isNaN(Number(v)) ? null : Number(v);
};

export async function changeRule(form: FormData): Promise<void> {
  const me = await requireStaff();
  const classId = text(form, "class_id");
  const back = (q: string) => redirect(`/timetable/rules?${classId ? `class=${classId}&` : ""}${q}`);
  const date = text(form, "on_date");
  let res: Response;
  try {
    res = await engineSend("/timetable/rules/change", {
      actor: me.email,
      class_id: classId,
      rule: text(form, "rule") ?? "",
      action: text(form, "action") ?? "set",
      id: text(form, "id"),
      period_id: text(form, "period_id"),
      starts_at: text(form, "starts_at"),
      ends_at: text(form, "ends_at"),
      label: text(form, "label"),
      on_date: date,
      weekday: date ? null : num(form, "weekday"),
      week_code: date ? null : text(form, "week_code"),
      reason: text(form, "reason"),
      subject_code: text(form, "subject_code"),
      span: text(form, "span"),
      fewest: num(form, "fewest"),
      most: num(form, "most"),
      text: text(form, "text"),
    });
  } catch (e) {
    if (e instanceof EngineDown) return back(`error=${encodeURIComponent(e.message)}`);
    throw e;
  }
  if (!res.ok) return back(`error=${encodeURIComponent(await refusal(res, "That was not saved."))}`);
  return back("saved=1");
}
