"use server";

import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { EngineDown, engineSend, voiceTicket } from "@/lib/engine";
import { myVoice, refusal, voiceOn } from "@/lib/voice";
import { W } from "@/lib/voice-words";
import type { Sent } from "./board";

// The K2 voice notes' three writes (task M1-04), each the engine's (routes/voice.py) with her email as `actor`: her
// recording's ticket, a note confirmed, the form saved. A refusal comes back in the engine's own words, on the page.

/** Voice notes switched on, after the action has checked who is asking (`requireStaff`, in the action itself). */
async function switchedOn() {
  if (!(await voiceOn())) redirect("/today");
}

/** Leave for this page to send her recording straight to the engine (a ticket good for half an hour). */
export async function recordTicket(): Promise<{ url: string; token: string } | null> {
  const me = await requireStaff();
  await switchedOn();
  if (!(await myVoice(me))?.recording) return null; // D-065: no ticket to send a recording while recording is off
  return voiceTicket(me.email);
}

async function written(res: Promise<Response>, fallback: string): Promise<{ error: string } | void> {
  let got: Response;
  try {
    got = await res;
  } catch (e) {
    if (e instanceof EngineDown) return { error: fallback };
    throw e;
  }
  if (!got.ok) return { error: await refusal(got, fallback) };
  redirect("/today?open=notes&voice=saved");
}

export async function confirmNote(noteId: string, s: Sent): Promise<{ error: string } | void> {
  const me = await requireStaff();
  await switchedOn();
  return written(engineSend("/voice/notes/confirm", { actor: me.email, note_id: noteId, ...s }), W.confirm.notSaved);
}

export async function saveForm(classId: string, s: Sent): Promise<{ error: string } | void> {
  const me = await requireStaff();
  await switchedOn();
  return written(engineSend("/voice/form", { actor: me.email, class_id: classId, ...s }), W.form.notSaved);
}
