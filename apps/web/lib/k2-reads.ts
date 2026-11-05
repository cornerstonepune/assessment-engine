import { ENGINE_RESTARTING, EngineDown, engineSend } from "./engine";
import type { ChildPage, ClassPicture } from "./k2-child";

// The two K2 reads, as a page asks for them (task M1-17). A refusal is an answer, not a crash: the engine says no while
// the educator switch is off (403 "not switched on") or when the class is not the person's (403), and 404 for a class or
// a Sr. No. that is not there. The page shows the engine's own words.
export type Read<T> = { ok: true; value: T } | { ok: false; status: number; message: string };

async function read<T>(path: "/k2/picture" | "/k2/child" | "/k2/classes", body: Record<string, string>): Promise<Read<T>> {
  let res: Response;
  try {
    res = await engineSend(path, body as never);
  } catch (e) {
    if (e instanceof EngineDown) return { ok: false, status: 503, message: ENGINE_RESTARTING };
    throw e;
  }
  const json = (await res.json().catch(() => ({}))) as { detail?: string } & Record<string, unknown>;
  if (res.ok) return { ok: true, value: json as T };
  return { ok: false, status: res.status, message: typeof json.detail === "string" ? json.detail : "This is not available." };
}

export const classPicture = (actor: string, classId: string) => read<ClassPicture>("/k2/picture", { actor, class_id: classId });
export const childPage = (actor: string, classId: string, roll: string) => read<ChildPage>("/k2/child", { actor, class_id: classId, roll_no: roll });

export type K2Class = { id: string; grade: string; section: string };
/** The classes the pictures list for her: her own, and for the staff preview every class whose timetable is in force today. */
export const k2Classes = (actor: string) => read<{ classes: K2Class[] }>("/k2/classes", { actor });
