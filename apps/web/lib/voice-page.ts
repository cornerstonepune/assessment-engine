import { notFound } from "next/navigation";
import type { Session } from "./auth";
import { myVoice, voiceOn } from "./voice";
import { classWords, SCHOOL_ZONE, type MyVoice, type VoiceClass } from "./voice-types";

// What every K2 page asks after it has checked who is asking (`requireStaff`, in the page itself: test_web_gate.py):
// voice notes switched on, and a K2 class or a note of hers. Anything else is not found, a typed address as much as a
// link; when the address names a class, `chosenClass` holds it to one of hers.
export async function herVoice(me: Session): Promise<MyVoice> {
  if (!(await voiceOn())) notFound();
  const my = await myVoice(me);
  if (!my) notFound();
  return my;
}

/** The class the address names, else her only class; null when she has several and named none. */
export function chosenClass(my: MyVoice, id: string | undefined): (VoiceClass & { words: string }) | null {
  const c = id ? my.classes.find((x) => x.id === id) : my.classes.length === 1 ? my.classes[0] : undefined;
  if (id && !c) notFound();
  return c ? { ...c, words: classWords(c) } : null;
}

/** Today on the school's clock, as a date input reads it. */
export const schoolToday = () => new Date().toLocaleDateString("en-CA", { timeZone: SCHOOL_ZONE });
