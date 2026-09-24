// A library worksheet printed for the children an educator ticks: one copy each, each with its own code, so a
// scan of them sorts itself onto each child. The engine records every copy in the educator's name.
import { currentStaff } from "@/lib/auth";
import { EngineDown, engineSend } from "@/lib/engine";
import { isoWeek } from "@/lib/week";

const CODE = /^[RMX]\d{1,2}-[EMHA]\d{2,3}$/;
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request: Request, { params }: { params: Promise<{ code: string }> }) {
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  const { code } = await params;
  if (!CODE.test(code)) return new Response("no such worksheet", { status: 404 });
  const children = (await request.formData()).getAll("child").map(String).filter((c) => ID.test(c));
  if (!children.length) return new Response("Tick at least one child to print for.", { status: 400 });
  try {
    const res = await engineSend(`/worksheet/${code}/for.pdf`, { children, week: isoWeek(), by: me.email });
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail;
      return new Response(why ?? "the engine could not print the worksheet", { status: res.status });
    }
    return new Response(res.body, {
      headers: { "content-type": "application/pdf", "content-disposition": `inline; filename=${code}.pdf`, "cache-control": "no-store" },
    });
  } catch (e) {
    return new Response(e instanceof EngineDown ? e.message : "could not print the worksheet", { status: 503 });
  }
}
