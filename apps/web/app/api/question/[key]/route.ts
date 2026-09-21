import { currentStaff } from "@/lib/auth";
import { engineImage } from "@/lib/engine";

const KEY = /^[A-Za-z0-9._-]+$/;

/** One question exactly as a paper prints it, for its page in the bank. The engine draws it with the
 *  paper's own renderer and stylesheet; this hands the picture to signed-in staff only. */
export async function GET(_: Request, { params }: { params: Promise<{ key: string }> }) {
  if (!(await currentStaff())) return new Response("sign in first", { status: 401 });
  const { key } = await params;
  if (!KEY.test(key)) return new Response("no such question", { status: 400 });
  return engineImage(`/bank/item/${key}/printed.png`);
}
