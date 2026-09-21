"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { EngineDown, enginePost } from "@/lib/engine";

const UUID = /^[0-9a-f-]{36}$/;
// The validation queue sends its answers here too; after one is settled it goes back to the queue,
// at the same place, where the next answer now stands. Only that address is ever followed.
const QUEUE = /^\/capture\/check(\?from=\d{1,5})?$/;
const back = (formData: FormData) => {
  const next = String(formData.get("next") ?? "");
  return QUEUE.test(next) ? next : null;
};

/** A person says what the child actually wrote.
 *
 * The engine marks it again, because marking is a lookup against numbers computed when the paper
 * was entered and a teacher should never be asked to do arithmetic the engine can do. The
 * correction itself is a new row in `read_correction`; the engine's own reading is left exactly as
 * it was (rule 4), which is what keeps the reader measurable against the page afterwards. */
export async function correctRead(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("result_id") ?? "");
  const paper = String(formData.get("paper_id") ?? "");
  const wrote = String(formData.get("human_read") ?? "").trim().slice(0, 40);
  if (!UUID.test(id) || !UUID.test(paper)) redirect("/capture");
  try {
    await enginePost("/capture/correct", { result_id: id, human_read: wrote, by: me.email });
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    redirect(back(formData) ? "/capture/check?error=engine" : `/capture/${paper}?error=engine`);
  }
  revalidatePath(`/capture/${paper}`);
  revalidatePath("/capture/check");
  redirect(back(formData) ?? `/capture/${paper}?corrected=${encodeURIComponent(wrote || "blank")}#a-${id}`);
}

/** A person signs off ONE paper: every answer on it becomes evidence in their name, and the
 *  child's ladder is rebuilt from it. Scoped to this capture — a signature means the person read
 *  the thing they signed, not everything that child has ever sat. */
export async function confirmPaper(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const paper = String(formData.get("paper_id") ?? "");
  const child = String(formData.get("child_id") ?? "");
  if (!UUID.test(paper) || !UUID.test(child)) redirect("/capture");
  // One statement, one confirm per file of this sitting: a Grade 3 paper arrives as one
  // photograph per page, and signing off the paper means signing off all of it.
  const [{ n }] = await sql<{ n: number }[]>`
    select coalesce(sum(confirm_results(${child}::uuid, ${me.email}, c.id)), 0)::int as n
      from capture c where c.sheet_instance_id = ${paper}::uuid and c.superseded_by is null`;
  revalidatePath(`/capture/${paper}`);
  revalidatePath(`/growth/${child}`);
  redirect(`/capture/${paper}?confirmed=${n}`);
}

/** The few answers code cannot mark — a comparison symbol, "find the mistake" — where only a
 *  person can say whether the child was right. The reading is theirs already; this is the
 *  judgement, and it is asked for nowhere else on the screen. */
export async function judgeRead(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("result_id") ?? "");
  const paper = String(formData.get("paper_id") ?? "");
  const status = String(formData.get("status") ?? "");
  if (!UUID.test(id) || !UUID.test(paper)) redirect("/capture");
  if (!["correct", "wrong", "blank"].includes(status)) redirect(`/capture/${paper}?error=judge`);
  await sql`select resolve_result(${id}::uuid, ${status}, '{}'::text[], ${me.email})`;
  revalidatePath(`/capture/${paper}`);
  revalidatePath("/capture/check");
  redirect(back(formData) ?? `/capture/${paper}?confirmed=1`);
}

/** From the queue: a person judges ONE answer only a person can mark — right, wrong or blank — and
 *  nothing else. `judgeRead` signs off the whole page as well, which is right on the paper's own
 *  screen, where the person has the page in front of them; in the queue they have seen one answer.
 *  Who judged it is kept as a `read_correction` row whose reading is the engine's own, unchanged. */
export async function judgeOne(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("result_id") ?? "");
  const status = String(formData.get("status") ?? "");
  const next = back(formData) ?? "/capture/check";
  if (!UUID.test(id) || !["correct", "wrong", "blank"].includes(status)) redirect(next);
  // One statement, so the judgement and the record of who made it land together or not at all.
  await sql`
    with judged as (
      update item_result set status = ${status}, misconception_codes = '{}', updated_at = now()
      where id = ${id}::uuid and state = 'candidate' and status = 'needs_teacher'
      returning tenant_id, capture_id, coalesce(raw_read::jsonb ->> 'child_answer', '') as read
    )
    insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by)
    select j.tenant_id, si.child_id, c.id, ${id}::uuid, j.read, j.read, ${me.email}
    from judged j join capture c on c.id = j.capture_id join sheet_instance si on si.id = c.sheet_instance_id`;
  revalidatePath("/capture/check");
  redirect(next);
}
