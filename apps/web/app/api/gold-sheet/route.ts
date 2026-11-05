// The sheet of drafted K2 pages for people to mark keep, change or reject (task M1-11h). It holds the school's lesson text
// beside the draft, and this repository and its logs are public, so it is sent to the signed-in member of staff's browser
// as a download and nowhere else: no page renders it, nothing writes it to disk, and the engine leaves off everything the
// machine said of a draft (`w1_bank/k2_gold.py`).
import { currentStaff } from "@/lib/auth";
import { EngineDown, engineGet } from "@/lib/engine";

export async function GET(request: Request) {
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  const asked = Number(new URL(request.url).searchParams.get("pages") ?? 30);
  const pages = Number.isInteger(asked) && asked >= 1 && asked <= 100 ? asked : 30;
  try {
    const res = await engineGet(`/curriculum/gold-sheet.csv?by=${encodeURIComponent(me.email)}&pages=${pages}`);
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail;
      return new Response(why ?? "the engine could not make the sheet", { status: res.status });
    }
    return new Response(res.body, {
      headers: {
        "content-type": "text/csv; charset=utf-8",
        "content-disposition": 'attachment; filename="k2-drafts-to-mark.csv"',
        "cache-control": "no-store",
      },
    });
  } catch (e) {
    return new Response(e instanceof EngineDown ? e.message : "could not make the sheet", { status: 503 });
  }
}
