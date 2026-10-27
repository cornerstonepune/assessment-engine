"use server";

import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { after } from "next/server";
import { requireStaff } from "./auth";
import { limits, reporterMark, saveNote, sendWaiting, tooMany } from "./feedback";
import { browserOf, HOW_OFTEN, KINDS, refusal, routeOnly, type HowOften, type NoteKind } from "./feedback-words";

// "Report a problem or suggest something" (goals/feed_report_from_the_tool.yaml): staff only, checked here again as
// every action is. The note is saved before anything else; GitHub is tried after the answer has gone back, so the person
// is thanked whether or not GitHub answers, and only once the note is kept.

/** What the person is told; when a note is refused, what they typed comes back so the boxes keep it. */
export type Said = { ok: boolean; words: string; kept?: Record<string, string> } | null;

export async function submitNote(_: Said, form: FormData): Promise<Said> {
  const me = await requireStaff();
  const kind = String(form.get("kind") ?? "") as NoteKind;
  const doing = String(form.get("doing") ?? "").trim();
  const happened = String(form.get("happened") ?? "").trim();
  const often = String(form.get("how_often") ?? "");
  const no = (words: string): Said => ({ ok: false, words, kept: { kind, doing, happened, how_often: often } });
  if (!(kind in KINDS)) return no("Please choose what kind of note this is.");
  if (!doing || !happened) return no("Please fill in both boxes.");
  const { perHour, maxChars } = await limits();
  if (doing.length > maxChars || happened.length > maxChars) {
    return no(`Please keep each box under ${maxChars} characters.`);
  }
  const refused = refusal(doing, happened);
  if (refused) return no(refused);
  const reporter = reporterMark(me.email);
  if (await tooMany(reporter, perHour)) {
    return no(`You have sent ${perHour} notes in the last hour. Please wait a little before the next one.`);
  }
  const head = await headers();
  const id = await saveNote(
    {
      kind,
      doing,
      happened,
      howOften: kind === "bug" && (HOW_OFTEN as readonly string[]).includes(often) ? (often as HowOften) : null,
      route: routeOnly(String(form.get("from") ?? "/")),
      role: me.role,
      classes: me.role === "coordinator" ? "" : (me.classes ?? []).join(", "),
      browser: browserOf(head.get("user-agent") ?? ""),
    },
    reporter,
  );
  after(() => sendWaiting(id));
  revalidatePath("/feedback");
  return { ok: true, words: "Thanks, we have your note." };
}
