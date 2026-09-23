// A child's paper exactly as it will print, before anyone approves it: the home paper the engine proposes, or,
// with `a` (skill~level~n, repeated), the paper a teacher is choosing. The engine renders it and saves nothing.
import { currentStaff } from "@/lib/auth";
import { EngineDown, engineGet, engineSend } from "@/lib/engine";
import { readArea } from "@/lib/next-paper";

const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request: Request, { params }: { params: Promise<{ child: string }> }) {
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  const { child } = await params;
  const q = new URL(request.url).searchParams;
  const week = q.get("week") ?? "";
  if (!ID.test(child) || !week) return new Response("no such paper", { status: 404 });
  const areas = q.getAll("a").map(readArea).filter((a) => a !== null);
  try {
    const res = areas.length
      ? await engineSend(`/child/${child}/paper/plan.pdf`, { week, by: me.email, areas })
      : await engineGet(`/child/${child}/focus/paper.pdf?week=${encodeURIComponent(week)}&by=${encodeURIComponent(me.email)}`);
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail;
      return new Response(why ?? "the engine could not make the paper", { status: res.status });
    }
    return new Response(res.body, {
      headers: { "content-type": "application/pdf", "content-disposition": "inline; filename=paper.pdf", "cache-control": "no-store" },
    });
  } catch (e) {
    return new Response(e instanceof EngineDown ? e.message : "could not make the paper", { status: 503 });
  }
}
