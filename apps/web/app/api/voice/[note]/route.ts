import { currentStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";
import { myVoice, voiceOn } from "@/lib/voice";

const UUID = /^[0-9a-f-]{36}$/;

/** Her own recording, to play beside her note (task M1-04): the engine hands it only to the educator who made it. */
export async function GET(_: Request, { params }: { params: Promise<{ note: string }> }) {
  if (!(await voiceOn())) return new Response("not found", { status: 404 });
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  const { note } = await params;
  if (!UUID.test(note)) return new Response("not found", { status: 404 });
  if (!(await myVoice(me))?.recording) return new Response("not found", { status: 404 }); // D-065
  try {
    const res = await engineSend("/voice/notes/audio", { actor: me.email, note_id: note });
    if (!res.ok) return new Response("not found", { status: res.status === 403 ? 403 : 404 });
    return new Response(res.body, { headers: { "content-type": res.headers.get("content-type") ?? "application/octet-stream", "cache-control": "private, no-store" } });
  } catch (e) {
    if (e instanceof EngineDown) return new Response(e.message, { status: 503 });
    throw e;
  }
}
