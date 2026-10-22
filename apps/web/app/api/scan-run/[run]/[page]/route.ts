import { currentStaff } from "@/lib/auth";
import { engineImage } from "@/lib/engine";

const UUID = /^[0-9a-f-]{36}$/;

/** One page of a file sent to be read, small, for a person to see whose it is before giving it to a child
 *  (goals/ux9a-no-guessed-pages.yaml): a page on which no code could be read has no child and no class yet, so any
 *  member of staff signed in may see it, as with a scan not yet sorted (`/api/scan`). */
export async function GET(_request: Request, { params }: { params: Promise<{ run: string; page: string }> }) {
  if (!(await currentStaff())) return new Response("sign in first", { status: 401 });
  const { run, page } = await params;
  const n = Number(page);
  if (!UUID.test(run) || !Number.isInteger(n) || n < 1 || n > 999) return new Response("no such page", { status: 400 });
  return engineImage(`/read/run/${run}/page/${n}.jpg`);
}
