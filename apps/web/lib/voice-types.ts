// The shapes of the engine's K2 voice answers the website reads (routes/voice.py), with no database or engine call, so
// What needs doing's pure list (lib/todo.ts) can use them.
export type VoiceClass = { id: string; grade: string; section: string };
export type QueuedNote = { id: string; class_id: string; status: string; received_at: string };
/** `recording`: both switches on (D-065), so she may record and hear a note back; off, she uses the form. */
export type MyVoice = { classes: VoiceClass[]; notes: QueuedNote[]; recording: boolean };

/** "K2 A": a class as she reads it. */
export const classWords = (c: Pick<VoiceClass, "grade" | "section">) => (c.section.startsWith(c.grade) ? c.section : `${c.grade} ${c.section}`);

/** The school's clock, as the other pages read it (config `school.time_zone` on the engine's side). */
export const SCHOOL_ZONE = "Asia/Kolkata";
