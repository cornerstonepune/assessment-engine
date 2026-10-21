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
  child_id: string | null;
  answers: number;
  skipped?: boolean;
  why?: string;
  lacks?: string[];
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
};

const pagesSaid = (ps: number[]) => (ps.length === 1 ? `page ${ps[0]}` : `pages ${ps.join(", ")}`);

/** The `n` files read last — those with a copy of the person's classes, or with none of any class's — newest first. */
export async function lastScans(scope: Scope = EVERY_CLASS, n = 3): Promise<Scan[]> {
  const runs = await sql<{ id: string; trigger: string | null; when: string; status: Scan["status"]; error: string | null; copies: Copy[] }[]>`
    select id, trigger, to_char(started_at at time zone 'Asia/Kolkata', 'DD-Mon-YYYY HH24:MI') as when, status, error,
           coalesce(result -> 'copies', '[]'::jsonb) as copies
    from flow_run where flow = 'read-scan' order by started_at desc limit ${scope.classes ? 4 * n : n}`;
  const ids = [...new Set(runs.flatMap((r) => r.copies.flatMap((c) => (c.child_id ? [c.child_id] : []))))];
  const kids = new Map(
    (ids.length ? await sql<{ id: string; section: string; roll_no: string }[]>`
      select id, section, roll_no from child where id = any(${ids}::uuid[])` : []).map((k) => [k.id, k]),
  );
  const classOf = (c: Copy) => (c.child_id ? kids.get(c.child_id)?.section ?? null : null);
  return runs
    .filter((r) => !scope.classes || r.copies.every((c) => !classOf(c)) || r.copies.some((c) => isMine(scope, classOf(c))))
    .slice(0, n)
    .map((r) => {
      const read = r.copies.filter((c) => !c.skipped);
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
      };
    });
}
