import { currentStaff } from "@/lib/auth";
import { captureSection, isMine, notYoursResponse, scopeOf } from "@/lib/scope";
import { engineImage } from "@/lib/engine";

const UUID = /^[0-9a-f-]{36}$/;
const BOX = /^-?\d+(\.\d+)?(,-?\d+(\.\d+)?){3}$/;

/** The photograph behind one reading, for the approval screen to put beside it.
 *
 * The scan never enters the database or git, so it cannot be served from a row: the engine reads
 * it off the school's disk and this hands it on, signed in, cropped to the region the answer was
 * read from. Nobody who is not signed in gets a child's handwriting. */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ capture: string; page: string }> },
) {
  const me = await currentStaff();
  if (!me) return new Response("sign in first", { status: 401 });
  const { capture, page } = await params;
  const n = Number(page);
  if (!UUID.test(capture) || !Number.isInteger(n) || n < 1 || n > 99) {
    return new Response("no such page", { status: 400 });
  }
  // a scan not yet sorted onto any paper has no class, and stays open to whoever is reading the pile
  const section = await captureSection(capture);
  if (section !== null && !isMine(scopeOf(me), section)) return notYoursResponse();
  const box = new URL(request.url).searchParams.get("box") ?? "";
  const q: "" | `?box=${string}` = BOX.test(box) ? `?box=${box}` : "";
  return engineImage(`/capture/${capture}/page/${n}.jpg${q}`);
}
