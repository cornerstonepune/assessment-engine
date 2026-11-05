// The two checkers' verdicts on the same drafted K2 pages, one row a page: each checker's faults beside the school's own
// words and the draft (task M1-12a). It holds the school's lesson text, and this repository and its logs are public, so it
// is sent to the signed-in member of staff's browser as a download and nowhere else: no page renders it and nothing
// writes it to disk. Counts and cost, which hold none of the school's words, are the `checkers` run of the workflow.
import { currentStaff } from "@/lib/auth";
import { EngineDown, engineGet } from "@/lib/engine";

export async function GET() {
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  try {
    const res = await engineGet(`/curriculum/checkers.csv?by=${encodeURIComponent(me.email)}&stage=dev_eval`);
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail;
      return new Response(why ?? "the engine could not make the sheet", { status: res.status });
    }
    return new Response(res.body, {
      headers: {
        "content-type": "text/csv; charset=utf-8",
        "content-disposition": 'attachment; filename="k2-two-checkers.csv"',
        "cache-control": "no-store",
      },
    });
  } catch (e) {
    return new Response(e instanceof EngineDown ? e.message : "could not make the sheet", { status: 503 });
  }
}
