"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { engineSend, markWhatTrustSettles } from "@/lib/engine";
import { makePaper } from "@/lib/next-paper";

const UUID = /^[0-9a-f-]{36}$/;

/** A person stands behind the machine's marking of this child's papers: every candidate the
 *  marker could settle becomes evidence, and the map is rebuilt from it. */
export async function confirmChild(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  if (!UUID.test(id)) redirect("/growth");
  const [{ n }] = await sql<
    { n: number }[]
  >`select confirm_results(${id}::uuid, ${me.email}) as n`;
  const marked = await markWhatTrustSettles(); // a sign-off may be what earns a kind the reader's trust
  revalidatePath(`/growth/${id}`);
  revalidatePath("/capture/check");
  redirect(`/growth/${id}?confirmed=${n}${marked ? "" : "&later=1"}`);
}

/** A person settles one answer the machine could not read or mark. */
export async function resolveOne(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("result_id") ?? "");
  const child = String(formData.get("child_id") ?? "");
  const status = String(formData.get("status") ?? "");
  if (!UUID.test(id) || !UUID.test(child)) redirect("/growth");
  if (!["correct", "wrong", "blank"].includes(status))
    redirect(`/growth/${child}?error=resolve`);
  await sql`select resolve_result(${id}::uuid, ${status}, '{}'::text[], ${me.email})`;
  revalidatePath(`/growth/${child}`);
  redirect(`/growth/${child}?resolved=1`);
}

/** A teacher approves the child's next paper, proposed from their own ladder (goals/s11-focus-paper.yaml,
 *  u2-children.yaml). The engine proposes and prints; this is the approval, in the person's name. */
export async function approveNextPaper(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  const week = String(formData.get("week") ?? "");
  if (!UUID.test(id) || !/^\d{4}-W\d{2}$/.test(week)) redirect("/growth");
  const qr = await makePaper(id, week, me.email);
  revalidatePath(`/growth/${id}`);
  // already approved this week (a second click, or a colleague first): the page shows who approved it
  redirect(qr ? `/growth/${id}?paper=${qr}` : `/growth/${id}`);
}

/** An educator asks for the parent report to be written from the child's signed-off answers (goals/w4c-parent-report.yaml).
 *  The engine writes it and holds it to the facts; a draft that breaks them is never kept, and the page says why. */
export async function writeParentReport(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  if (!UUID.test(id)) redirect("/growth");
  const r = await engineSend(`/child/${id}/parent-report`, {
    by: me.email,
  }).catch(() => null);
  // the engine answers at once and writes after: the page watches the run it names
  const run = r?.ok
    ? ((await r.json().catch(() => null)) as { run_id?: string } | null)?.run_id
    : null;
  revalidatePath(`/growth/${id}/parent`);
  redirect(
    `/growth/${id}/parent${run ? `?writing=${run}` : `?error=${r?.status ?? "down"}`}`,
  );
}

/** An educator approves the parent report, in their own name; only then is it the parents' to read. */
export async function approveParentReport(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  const note = String(formData.get("note_id") ?? "");
  if (!UUID.test(id) || !UUID.test(note)) redirect("/growth");
  const r = await engineSend(`/child/${id}/parent-report/${note}/approve`, {
    by: me.email,
  }).catch(() => null);
  revalidatePath(`/growth/${id}/parent`);
  redirect(
    `/growth/${id}/parent${r?.ok ? "?approved=1" : `?error=${r?.status ?? "down"}`}`,
  );
}

/** An educator's own words become the report: the draft's every part, the child's name turned back into [child] so
 *  no name is stored (rule 6), held by the engine to the same facts as the model's words. */
export async function editParentReport(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const id = String(formData.get("child_id") ?? "");
  const note = String(formData.get("note_id") ?? "");
  if (!UUID.test(id) || !UUID.test(note)) redirect("/growth");
  const name = String(formData.get("name") ?? "").trim();
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const named = name ? new RegExp(`\\b${escaped}\\b`, "g") : null;
  const back = (v: FormDataEntryValue | null | undefined) =>
    (named
      ? String(v ?? "").replace(named, "[child]")
      : String(v ?? "")
    ).trim();
  const all = (k: string) => formData.getAll(k);
  const draft = {
    summary: back(formData.get("summary")),
    can_do: all("can_do_id").map((c, i) => ({
      id: String(c),
      sentence: back(all("can_do_text")[i]),
    })),
    working_on: all("working_id").map((w, i) => ({
      id: String(w),
      explanation: back(all("working_text")[i]),
    })),
    at_home: all("at_home").map(back).filter(Boolean),
  };
  const r = await engineSend(`/child/${id}/parent-report/${note}/edit`, {
    by: me.email,
    draft,
  }).catch(() => null);
  revalidatePath(`/growth/${id}/parent`);
  if (r?.ok) redirect(`/growth/${id}/parent?edited=1`);
  const problems =
    r?.status === 422
      ? ((
          (await r.json().catch(() => null)) as {
            detail?: { problems?: string[] };
          } | null
        )?.detail?.problems ?? [])
      : [];
  redirect(
    `/growth/${id}/parent?edit=1&${problems.length ? `problems=${encodeURIComponent(problems.slice(0, 5).join("\n"))}` : `error=${r?.status ?? "down"}`}`,
  );
}
