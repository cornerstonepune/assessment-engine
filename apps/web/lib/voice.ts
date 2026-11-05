import { cache } from "react";
import type { Session } from "./auth";
import { sql } from "./db";
import { EngineDown, enginePost, engineSend } from "./engine";
import type { Activity, Draft } from "./voice-check";
import type { MyVoice } from "./voice-types";

// The K2 voice notes as the website reads them (task M1-04). Everything about a note is the engine's (routes/voice.py):
// her classes from her role grant, her notes waiting, a note's draft, her recording; the site never looks a person up by
// email. All of it behind the switch `voice.screens_enabled` (config, false): while it is off, nothing here is shown.

export { classWords } from "./voice-types";

export const voiceOn = cache(async (): Promise<boolean> => {
  const [row] = await sql<{ on: boolean }[]>`select coalesce((select value = 'true'::jsonb from config where key = 'voice.screens_enabled'), false) as on`;
  return row?.on ?? false;
});

/** Her K2 classes and her notes waiting, or null: switched off, not on the staff list, or the engine not answering
 *  (What needs doing still opens; the K2 groups are left out). Once per request, for the menu's count and the page. */
export const myVoice = cache(async (me: Pick<Session, "email">): Promise<MyVoice | null> => {
  if (!(await voiceOn())) return null;
  try {
    const got = (await enginePost("/voice/queue", { actor: me.email })) as MyVoice;
    return got.classes.length || got.notes.length ? got : null;
  } catch (e) {
    if (e instanceof EngineDown) return null;
    throw e;
  }
});

/** One of her notes, drafted: null when it is not hers (or not a note). */
export async function draftOf(me: Pick<Session, "email">, noteId: string): Promise<Draft | null> {
  const res = await engineSend("/voice/notes/draft", { actor: me.email, note_id: noteId });
  if (res.status === 404) return null;
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}).`);
  return (await res.json()) as Draft;
}

/** Every activity of a grade, for the picker: those with the K2 team's number first, by number, then those the sheet
 *  left without one, by name (321 of live's 871 K2 activities; each is found by its name, none is out of reach). */
export const activitiesOf = cache(
  (grade: string) =>
    sql<Activity[]>`
      select code, case when sheet_no ~ '^[0-9]+$' then sheet_no else '' end as no, name from activity
      where band = ${grade}
      order by (sheet_no !~ '^[0-9]+$'), case when sheet_no ~ '^[0-9]+$' then sheet_no::int end, name, code`,
);

/** The engine's reason, in its own words, or ours when it gave none. */
export async function refusal(res: Response, fallback: string): Promise<string> {
  const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
  return typeof body.detail === "string" ? body.detail : fallback;
}
