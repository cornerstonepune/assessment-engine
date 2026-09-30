// Papers made together, printed together: the engine merges each paper exactly as it was rendered, in class and
// roll order, into one PDF (`w2_print/maker.py`). Nothing is drawn again and nothing is written.
import { currentStaff } from "@/lib/auth";
import { EngineDown, engineGet } from "@/lib/engine";

const QR = /^CS[0-9A-F]{6}$/;

export async function GET(request: Request) {
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  const qrs = new URL(request.url).searchParams.getAll("qr").filter((q) => QR.test(q));
  if (!qrs.length) return new Response("no such paper", { status: 404 });
  try {
    const res = await engineGet(`/papers/pack.pdf?${qrs.map((q) => `qr=${q}`).join("&")}`);
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail;
      return new Response(why ?? "the engine could not print the papers", { status: res.status });
    }
    return new Response(res.body, {
      headers: { "content-type": "application/pdf", "content-disposition": "inline; filename=papers.pdf", "cache-control": "no-store" },
    });
  } catch (e) {
    return new Response(e instanceof EngineDown ? e.message : "could not print the papers", { status: 503 });
  }
}
