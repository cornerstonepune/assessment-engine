import { notFound } from "next/navigation";
import { requireStaff } from "./auth";
import { myVoice, voiceOn } from "./voice";
import { classWords, SCHOOL_ZONE, type MyVoice, type VoiceClass } from "./voice-types";

// What every K2 page asks first (task M1-04): voice notes switched on, a person on the staff list with a K2 class, and,
// when the address names a class, one of hers. Anything else is not found, a typed address as much as a link.
export async function herVoice(): Promise<{ me: Awaited<ReturnType<typeof requireStaff>>; my: MyVoice }> {
  if (!(await voiceOn())) notFound();
  const me = await requireStaff();
  const my = await myVoice(me);
  if (!my) notFound();
  return { me, my };
}

/** The class the address names, else her only class; null when she has several and named none. */
export function chosenClass(my: MyVoice, id: string | undefined): (VoiceClass & { words: string }) | null {
  const c = id ? my.classes.find((x) => x.id === id) : my.classes.length === 1 ? my.classes[0] : undefined;
  if (id && !c) notFound();
  return c ? { ...c, words: classWords(c) } : null;
}

/** Today on the school's clock, as a date input reads it. */
export const schoolToday = () => new Date().toLocaleDateString("en-CA", { timeZone: SCHOOL_ZONE });
