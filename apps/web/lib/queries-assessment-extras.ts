// What the Assessments page adds to an assessment's own row (goals/asm_assessments_page.yaml): the name an educator chose
// for it, the files read that its printed codes belong to, and the photographed pages of a child's paper. Names no child.
import { sql } from "./db";
import { matchFiles } from "./assessment-steps";

const CODE = /^CS[0-9A-F]{6}$/i;

/** The newest name an educator gave each assessment, by its key; an assessment never named has none (append-only). */
export async function chosenNames(keys: string[]): Promise<Map<string, string>> {
  if (!keys.length) return new Map();
  const rows = await sql<{ key: string; name: string }[]>`
    select distinct on (key) key, name from assessment_name where key = any(${keys}) order by key, created_at desc, id desc`;
  return new Map(rows.map((r) => [r.key, r.name]));
}

/** The last files read, each listed against the assessment its codes belong to (`rows`: key and the codes of its
 *  copies); a file whose codes belong to no paper the school printed is listed apart, to be said as not matched. */
export async function fileLinks(rows: readonly { key: string; qrs: string[] }[], n = 40) {
  const runs = await sql<{ trigger: string | null; copies: { code?: string }[] }[]>`
    select trigger, coalesce(result -> 'copies', '[]'::jsonb) as copies from flow_run
    where flow = 'read-scan' and status <> 'running' order by started_at desc limit ${n}`;
  const scans = runs.map((r) => ({
    file: (r.trigger ?? "").split(": ").slice(1).join(": ") || "a scan",
    codes: r.copies.flatMap((c) => (c.code && CODE.test(c.code) ? [c.code.toUpperCase()] : [])),
  }));
  const all = [...new Set(scans.flatMap((s) => s.codes))];
  const known = new Set(
    all.length ? (await sql<{ qr: string }[]>`select qr_code as qr from sheet_instance where qr_code = any(${all})`).map((r) => r.qr.toUpperCase()) : [],
  );
  const owner = new Map(rows.flatMap((r) => (r.qrs ?? []).map((q) => [q.toUpperCase(), r.key] as const)));
  return matchFiles(scans, owner, known);
}

/** For papers that are read: the scan each is on and the pages of the file its answers were found on. */
export async function pagesOf(paperIds: string[]): Promise<Map<string, { capture: string; pages: number[] }>> {
  if (!paperIds.length) return new Map();
  const rows = await sql<{ id: string; capture: string; pages: number[] }[]>`
    select k.sheet_instance_id as id, k.id as capture,
           array_agg(distinct coalesce((r.raw_read::jsonb ->> 'file_page')::int, (r.raw_read::jsonb ->> 'page')::int, 1)) as pages
    from capture k join item_result r on r.capture_id = k.id
    where k.sheet_instance_id = any(${paperIds}::uuid[]) and k.superseded_by is null
    group by k.sheet_instance_id, k.id`;
  return new Map(rows.map((r) => [r.id, { capture: r.capture, pages: [...r.pages].sort((a, b) => a - b) }]));
}
