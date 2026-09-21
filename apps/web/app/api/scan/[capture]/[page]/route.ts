import { currentStaff } from "@/lib/auth";
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
  if (!(await currentStaff())) return new Response("sign in first", { status: 401 });
  const { capture, page } = await params;
  const n = Number(page);
  if (!UUID.test(capture) || !Number.isInteger(n) || n < 1 || n > 99) {
    return new Response("no such page", { status: 400 });
  }
  const box = new URL(request.url).searchParams.get("box") ?? "";
  const q = BOX.test(box) ? `?box=${box}` : "";
  return engineImage(`/capture/${capture}/page/${n}.jpg${q}`);
}
