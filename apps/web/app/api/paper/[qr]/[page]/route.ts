import { currentStaff } from "@/lib/auth";
import { engineImage } from "@/lib/engine";

const QR = /^CS[0-9A-F]{6}$/;

/** One page of a paper exactly as it was printed, QR code and all, for the paper view.
 *
 * The PDF lives on the school's disk beside the engine, like a scan, and carries the child's name
 * on their own page — so the engine opens it and this hands it on to signed-in staff only. */
export async function GET(_: Request, { params }: { params: Promise<{ qr: string; page: string }> }) {
  if (!(await currentStaff())) return new Response("sign in first", { status: 401 });
  const { qr, page } = await params;
  const n = Number(page);
  if (!QR.test(qr) || !Number.isInteger(n) || n < 1 || n > 99) {
    return new Response("no such page", { status: 400 });
  }
  return engineImage(`/sheet/${qr}/page/${n}.jpg`);
}
