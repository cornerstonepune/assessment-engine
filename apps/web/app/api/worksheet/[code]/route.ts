import { currentStaff } from "@/lib/auth";
import { engineImage } from "@/lib/engine";

const CODE = /^[RMX]\d{1,2}-[EMHA]\d{2,3}$/;

/** A library worksheet as it prints (ADR 0026). The engine renders it the first time anyone asks
 *  and keeps it; this hands the PDF on to a signed-in member of staff, and to no one else. */
export async function GET(_request: Request, { params }: { params: Promise<{ code: string }> }) {
  if (!(await currentStaff())) return new Response("sign in first", { status: 401 });
  const { code } = await params;
  if (!CODE.test(code)) return new Response("no such worksheet", { status: 404 });
  return engineImage(`/worksheet/${code}.pdf`);
}
