/**
 * What the last scans came to (goals/l11-a-scan-is-read-whole.yaml): each file sent to be read, from the site or the
 * Drive folder, and of its copies the ones a person must act on — a page of a child's paper not in the file, a page in
 * it twice, a copy not read and why — by class and roll number, never a name (rule 6). The engine keeps each copy's line
 * on the file's run (`inbox.read`) and words what it lacks (`copies._lacks`); this only says it, to the people whose
 * classes it is.
 */
import { sql } from "./db";
import { EVERY_CLASS, isMine, type Scope } from "./scope";

type Copy = {
  copy: number;
  pages: number[];
  code?: string;
  child_id: string | null;
  answers: number;
  skipped?: boolean;
  why?: string;
  lacks?: string[];
  capture_id?: string;
  no_code?: number[];
};

export type ScanLine = { who: string; said: string };
export type Scan = {
  id: string;
  file: string;
  when: string;
  status: "running" | "ok" | "error";
  error: string | null;
  read: number;
  answers: number;
  lines: ScanLine[];
  /** what the file held (goals/n8-upload-on-marking.yaml): its pages, its copies and the children they are, and of the
   *  answers read, how many the engine settled and how many wait for a person, as `answer_standing` says */
  pages: number | null;
  copies: number;
  children: number;
  engine: number;
  person: number;
  waiting: number;
  noCode: number[];
};

const pagesSaid = (ps: number[]) => (ps.length === 1 ? `page ${ps[0]}` : `pages ${ps.join(", ")}`);

/** The `n` files read last — those with a copy of the person's classes, or with none of any class's — newest first. */
export async function lastScans(scope: Scope = EVERY_CLASS, n = 5): Promise<Scan[]> {
  const runs = await sql<{ id: string; trigger: string | null; when: string; status: Scan["status"]; error: string | null; copies: Copy[]; pages: number | null }[]>`
    select id, trigger, to_char(started_at at time zone 'Asia/Kolkata', 'DD-Mon-YYYY HH24:MI') as when, status, error,
           coalesce(result -> 'copies', '[]'::jsonb) as copies, (result ->> 'pages')::int as pages
    from flow_run where flow = 'read-scan' order by started_at desc limit ${scope.classes ? 4 * n : n}`;
  const ids = [...new Set(runs.flatMap((r) => r.copies.flatMap((c) => (c.child_id ? [c.child_id] : []))))];
  const kids = new Map(
    (ids.length ? await sql<{ id: string; section: string; roll_no: string }[]>`
      select id, section, roll_no from child where id = any(${ids}::uuid[])` : []).map((k) => [k.id, k]),
  );
  const classOf = (c: Copy) => (c.child_id ? kids.get(c.child_id)?.section ?? null : null);
  const captures = [...new Set(runs.flatMap((r) => r.copies.flatMap((c) => (c.capture_id ? [c.capture_id] : []))))];
  const standing = new Map<string, { engine: number; person: number; waiting: number }>();
  for (const s of captures.length ? await sql<{ capture_id: string; engine: number; person: number; waiting: number }[]>`
      select r.capture_id, count(*) filter (where a.standing = 'engine')::int as engine,
             count(*) filter (where a.standing = 'person')::int as person,
             count(*) filter (where a.standing = 'waiting')::int as waiting
      from answer_standing a join item_result r on r.id = a.item_result_id
      where r.capture_id = any(${captures}::uuid[]) group by r.capture_id` : [])
    standing.set(s.capture_id, s);
  return runs
    .filter((r) => !scope.classes || r.copies.every((c) => !classOf(c)) || r.copies.some((c) => isMine(scope, classOf(c))))
    .slice(0, n)
    .map((r) => {
      const read = r.copies.filter((c) => !c.skipped);
      const seen = r.copies.filter((c) => !classOf(c) || isMine(scope, classOf(c)));
      const counted = seen.flatMap((c) => (c.capture_id ? [standing.get(c.capture_id) ?? { engine: 0, person: 0, waiting: 0 }] : []));
      // a page with no code: said by its number (`copies.read`'s no_code), or, on a run read before it was kept, the
      // pages of a copy not read for want of one
      const noCode = r.copies.flatMap((c) => c.no_code ?? (c.skipped && c.code === "?" ? c.pages : [])).sort((a, b) => a - b);
      const lines = r.copies.flatMap((c): ScanLine[] => {
        const k = c.child_id ? kids.get(c.child_id) : undefined;
        if (k && !isMine(scope, k.section)) return [];
        const who = k ? `${k.section} · roll ${k.roll_no}` : `Copy ${c.copy} (${pagesSaid(c.pages)})`;
        if (c.skipped) return [{ who, said: `not read — ${c.why ?? "no reason given"}` }];
        return (c.lacks ?? []).map((said) => ({ who, said }));
      });
      return {
        id: r.id,
        file: (r.trigger ?? "").split(": ").slice(1).join(": ") || "a scan",
        when: r.when,
        status: r.status,
        error: r.error,
        read: read.length,
        answers: read.reduce((n, c) => n + (c.answers ?? 0), 0),
        lines,
        pages: r.pages,
        copies: r.copies.length,
        children: new Set(seen.flatMap((c) => (c.child_id ? [c.child_id] : []))).size,
        engine: counted.reduce((n, c) => n + c.engine, 0),
        person: counted.reduce((n, c) => n + c.person, 0),
        waiting: counted.reduce((n, c) => n + c.waiting, 0),
        noCode,
      };
    });
}
