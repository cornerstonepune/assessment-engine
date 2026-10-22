"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding, mustBeMine } from "@/lib/decides";
import { childSection, paperSection, resultSection } from "@/lib/scope";
import { sql } from "@/lib/db";
import { EngineDown, enginePost, engineSend, markWhatTrustSettles, uploadTicket } from "@/lib/engine";

const UUID = /^[0-9a-f-]{36}$/;
// The validation queue sends its answers here too; after one is settled it goes back to the queue,
// at the same place, where the next answer now stands. Only that address is ever followed.
const QUEUE = /^\/capture\/check(\?from=\d{1,5})?$/;
const back = (formData: FormData) => {
  const next = String(formData.get("next") ?? "");
  return QUEUE.test(next) ? next : null;
};

/** A scan, by its Drive link, read without anyone at a terminal (N8, `POST /read/file`).
 *
 * The link is all that travels: the engine fetches the file into its own inbox, sorts the pages by
 * the code on each and reads every box on every copy printed for a child, after it has answered —
 * the papers appear on this page as they are read. The engine says in words why it will not take a
 * link, and that is what the person sees. */
export async function readScan(formData: FormData): Promise<void> {
  const me = await deciding("papers");
  // back to the page it was read from: Papers, or the scans and the reader's accuracy (goals/u9-papers.yaml)
  const page = formData.get("from") === "/papers" ? "/papers" : "/capture";
  const url = String(formData.get("url") ?? "")
    .trim()
    .slice(0, 400);
  if (!/^https:\/\/drive\.google\.com\//.test(url)) redirect(`${page}?read=not-a-link#read-scan`);
  try {
    const res = await engineSend("/read/file", { url, actor: me.email });
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "";
      redirect(`${page}?read=refused&why=${encodeURIComponent(why.slice(0, 200))}#read-scan`);
    }
    const { pages } = (await res.json()) as { pages: number };
    revalidatePath("/capture");
    revalidatePath("/papers");
    redirect(`${page}?read=started&pages=${Number(pages) || 0}#read-scan`);
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    redirect(`${page}?read=engine#read-scan`);
  }
}

/** A person says whose a page with no code is (goals/ux9a-no-guessed-pages.yaml, `POST /read/run/{id}/page`): the
 *  engine keeps their word on the file's run and reads the file again, the page as that child's. Until then the page is
 *  read as nobody's — the engine never guesses a page's child. The engine says in words why it will not. */
export async function givePage(formData: FormData): Promise<void> {
  const me = await deciding("papers");
  const page = formData.get("from") === "/papers" ? "/papers" : "/capture";
  const run = String(formData.get("run") ?? "");
  const child = String(formData.get("child") ?? "");
  const n = Number(formData.get("page"));
  if (!UUID.test(run) || !UUID.test(child) || !Number.isInteger(n) || n < 1) redirect(`${page}#read-scan`);
  mustBeMine(me, "papers", [await childSection(child)]);
  try {
    const res = await engineSend(`/read/run/${run}/page`, { page: n, child_id: child, by: me.email });
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "";
      redirect(`${page}?read=refused&why=${encodeURIComponent(why.slice(0, 200))}#read-scan`);
    }
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    redirect(`${page}?read=engine#read-scan`);
  }
  revalidatePath("/capture");
  revalidatePath("/papers");
  redirect(`${page}?read=given&pages=${n}#read-scan`);
}

/** A file already sent, read afresh (goals/ck2-photograph-is-its-page.yaml, `POST /read/run/{id}/again`): the engine reads
 *  every copy no person has worked on anew and supersedes only those readings; a person's checks stay. It takes no link
 *  — the file is the one the engine keeps — and says in words why it will not (still being read, no longer kept). */
export async function readAgain(formData: FormData): Promise<void> {
  const me = await deciding("papers");
  const page = formData.get("from") === "/papers" ? "/papers" : "/capture";
  const run = String(formData.get("run") ?? "");
  if (!UUID.test(run)) redirect(`${page}#read-scan`);
  try {
    const res = await engineSend(`/read/run/${run}/again`, { by: me.email });
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "";
      redirect(`${page}?read=refused&why=${encodeURIComponent(why.slice(0, 200))}#read-scan`);
    }
    const { pages } = (await res.json()) as { pages: number };
    revalidatePath("/capture");
    revalidatePath("/papers");
    redirect(`${page}?read=again&pages=${Number(pages) || 0}#read-scan`);
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    redirect(`${page}?read=engine#read-scan`);
  }
}

/** Leave to send scans from this page straight to the engine (N8, `POST /read/upload`, ADR 0092): where to, and a
 *  token for this person that lives half an hour — asked for as each batch of files starts, so a page left open all
 *  morning still sends. Only someone who may put papers in is given one. */
export async function scanTicket(): Promise<{ url: string; token: string } | null> {
  const me = await deciding("papers");
  return uploadTicket(me.email);
}

/** A person says what the child actually wrote.
 *
 * The engine marks it again, because marking is a lookup against numbers computed when the paper
 * was entered and a teacher should never be asked to do arithmetic the engine can do. The
 * correction itself is a new row in `read_correction`; the engine's own reading is left exactly as
 * it was (rule 4), which is what keeps the reader measurable against the page afterwards. */
export async function correctRead(formData: FormData): Promise<void> {
  const me = await deciding("answers");
  const id = String(formData.get("result_id") ?? "");
  const paper = String(formData.get("paper_id") ?? "");
  const wrote = String(formData.get("human_read") ?? "").trim().slice(0, 40);
  if (!UUID.test(id) || !UUID.test(paper)) redirect("/capture");
  mustBeMine(me, "answers", [await resultSection(id), await paperSection({ id: paper })]);
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

/** An educator changes the right answer of a paper's question, for every child (goals/s26-the-right-answer-shown-
 *  and-corrected.yaml, ADR 0045). Code checks it first and, refusing, says why in its own words; otherwise every
 *  child's answer to the question is marked again with it, and the page says how many were, and how many keep the
 *  mark a person gave them though the new right answer disagrees. */
export async function changeKey(formData: FormData): Promise<void> {
  const me = await deciding("questions");
  const id = String(formData.get("result_id") ?? "");
  const paper = String(formData.get("paper_id") ?? "");
  const slot = String(formData.get("slot") ?? "").slice(0, 12);
  const answer = String(formData.get("answer") ?? "").trim().slice(0, 40);
  if (!UUID.test(id) || !UUID.test(paper)) redirect("/capture");
  mustBeMine(me, "questions", [await resultSection(id), await paperSection({ id: paper })]);
  let to: string;
  try {
    const res = await engineSend("/paper/key", { result_id: id, answer, by: me.email });
    const body = (await res.json().catch(() => ({}))) as {
      detail?: string;
      now?: string;
      changed?: unknown[];
      left?: unknown[];
      unseen?: number;
    };
    const n = (body.changed?.length ?? 0) + (body.unseen ?? 0);
    const kept = body.left?.length ?? 0;
    to = res.ok
      ? `/capture/${paper}?key=${encodeURIComponent(`${slot}|${body.now ?? answer}|${n}|${kept}`)}#a-${id}`
      : `/capture/${paper}?error=${encodeURIComponent((body.detail ?? `refused (${res.status})`).slice(0, 200))}#a-${id}`;
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    to = `/capture/${paper}?error=engine#a-${id}`;
  }
  revalidatePath(`/capture/${paper}`);
  revalidatePath("/capture/check");
  redirect(to);
}

/** A person signs off ONE paper: every answer on it becomes evidence in their name, and the
 *  child's ladder is rebuilt from it. Scoped to this capture — a signature means the person read
 *  the thing they signed, not everything that child has ever sat. */
export async function confirmPaper(formData: FormData): Promise<void> {
  const me = await deciding("papers");
  const paper = String(formData.get("paper_id") ?? "");
  const child = String(formData.get("child_id") ?? "");
  if (!UUID.test(paper) || !UUID.test(child)) redirect("/capture");
  mustBeMine(me, "papers", [await paperSection({ id: paper }), await childSection(child)]);
  // One statement, one confirm per file of this sitting: a Grade 3 paper arrives as one
  // photograph per page, and signing off the paper means signing off all of it.
  const [{ n }] = await sql<{ n: number }[]>`
    select coalesce(sum(confirm_results(${child}::uuid, ${me.email}, c.id)), 0)::int as n
      from capture c where c.sheet_instance_id = ${paper}::uuid and c.superseded_by is null`;
  const marked = await markWhatTrustSettles(); // a sign-off may be what earns a kind the reader's trust
  revalidatePath(`/capture/${paper}`);
  revalidatePath(`/growth/${child}`);
  revalidatePath("/capture/check");
  redirect(`/capture/${paper}?confirmed=${n}${marked ? "" : "&later=1"}`);
}

/** The few answers code cannot mark — a comparison symbol, "find the mistake" — where only a
 *  person can say whether the child was right. The reading is theirs already; this is the
 *  judgement, and it is asked for nowhere else on the screen. */
export async function judgeRead(formData: FormData): Promise<void> {
  const me = await deciding("answers");
  const id = String(formData.get("result_id") ?? "");
  const paper = String(formData.get("paper_id") ?? "");
  const status = String(formData.get("status") ?? "");
  if (!UUID.test(id) || !UUID.test(paper)) redirect("/capture");
  mustBeMine(me, "answers", [await resultSection(id), await paperSection({ id: paper })]);
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
  const me = await deciding("answers");
  const id = String(formData.get("result_id") ?? "");
  const status = String(formData.get("status") ?? "");
  const next = back(formData) ?? "/capture/check";
  if (!UUID.test(id) || !["correct", "wrong", "blank"].includes(status)) redirect(next);
  mustBeMine(me, "answers", [await resultSection(id)]);
  // One statement, so the judgement and the record of who made it land together or not at all.
  await sql`
    with judged as (
      update item_result set status = ${status}, misconception_codes = '{}', updated_at = now()
      where id = ${id}::uuid and state = 'candidate' and status = 'needs_teacher'
      returning tenant_id, capture_id, coalesce(raw_read::jsonb ->> 'child_answer', '') as read
    )
    insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by, judged)
    select j.tenant_id, si.child_id, c.id, ${id}::uuid, j.read, j.read, ${me.email}, ${status}
    from judged j join capture c on c.id = j.capture_id join sheet_instance si on si.id = c.sheet_instance_id`;
  revalidatePath("/capture/check");
  redirect(next);
}

/** A person names the mistake behind a wrong answer no named mistake explains (goals/j2-name-the-mistake.yaml):
 *  one press on Jev's shortlist, any other named mistake, or none of them. The engine keeps it against this reading
 *  and it reaches the child's evidence when the paper is signed off. A refusal comes back in the engine's words. */
export async function nameMistake(formData: FormData): Promise<void> {
  const me = await deciding("answers");
  const id = String(formData.get("result_id") ?? "");
  const paper = String(formData.get("paper_id") ?? "");
  const code = String(formData.get("code") ?? "").slice(0, 80);
  if (!UUID.test(id) || !UUID.test(paper) || !code) redirect("/capture");
  mustBeMine(me, "answers", [await resultSection(id), await paperSection({ id: paper })]);
  // Jev's shortlist as the person saw it, [[code, chance], …], as the engine takes it; anything else is not kept
  let proposed: unknown[][] = [];
  try {
    const sent: unknown = JSON.parse(String(formData.get("proposed") ?? "[]"));
    if (Array.isArray(sent)) proposed = sent.filter((x): x is unknown[] => Array.isArray(x));
  } catch {
    proposed = [];
  }
  let why = "";
  try {
    const res = await engineSend("/capture/mistake", { result_id: id, code, by: me.email, proposed });
    if (!res.ok) why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? `refused (${res.status})`;
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    why = "the engine could not be reached";
  }
  revalidatePath(`/capture/${paper}`);
  redirect(why ? `/capture/${paper}?error=${encodeURIComponent(why.slice(0, 200))}#a-${id}` : `/capture/${paper}#a-${id}`);
}
