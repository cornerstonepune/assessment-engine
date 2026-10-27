/**
 * What the last scans came to (goals/l11-a-scan-is-read-whole.yaml): each file sent to be read, from the site or the
 * Drive folder, and of its copies the ones a person must act on — a page of a child's paper not in the file, a page in
 * it twice, a copy not read and why — by class and roll number, never a name (rule 6). The engine keeps each copy's line
 * on the file's run (`inbox.read`) and words what it lacks (`copies._lacks`); this only says it, to the people who see
 * it (`staff_sees`, lib/reach.ts): the file to whoever put it in or sees a paper read from it, each copy to whoever sees
 * that paper (goals/own_who_sees_answers.yaml).
 */
import { sql } from "./db";
import type { Session } from "./auth";
import { reachOf, seesCapture, seesRun, seesUploader } from "./reach";
import { isMine } from "./scope";

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
  by_code?: boolean;
  missing?: number[];
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
  /** the file's pages on which no code could be read and nobody has yet said whose they are: read as no child's until a
   *  person gives each to a child whose own paper is in the file (goals/ux9a-no-guessed-pages.yaml) */
  noCode: number[];
  /** the children a page may be given to, by class and roll: those of the person's classes whose own paper is in the
   *  file, a copy short of a page first */
  owners: { id: string; who: string; short: boolean }[];
  /** each page a person has given to a child, and to whom */
  given: { page: number; who: string }[];
  /** the file's other readings, newest first: a file read again is one line, its attempts inside it (Nimish,
   *  2026-10-26: five "reading stopped" lines for one file) */
  attempts: { when: string; status: Scan["status"]; error: string | null }[];
};

const pagesSaid = (ps: number[]) => (ps.length === 1 ? `page ${ps[0]}` : `pages ${ps.join(", ")}`);

type Run = { mine: boolean } & { id: string; file: string | null; when: string; status: Scan["status"]; error: string | null; copies: Copy[]; pages: number | null; given: { page: number; child_id: string }[] };

/** A file's runs, newest first, as one: the reading that stands — the one going on, else the newest that finished,
 *  else the newest — and the others as its attempts. */
function byFile(runs: Run[]): { run: Run; others: Run[] }[] {
  const files = new Map<string, Run[]>();
  for (const r of runs) files.set(r.file ?? r.id, [...(files.get(r.file ?? r.id) ?? []), r]);
  return [...files.values()].map((all) => {
    const run = all.find((r) => r.status === "running") ?? all.find((r) => r.status === "ok") ?? all[0];
    return { run, others: all.filter((r) => r !== run) };
  });
}

/** The `n` files read last — those with a copy of the person's classes, or with none of any class's — newest first,
 *  each file once however many times it was read (`byFile`). */
export async function lastScans(me: Session, n = 5): Promise<Scan[]> {
  const scope = await reachOf(me);
  const runs = await sql<Run[]>`
    select id, coalesce(result ->> 'file', substr(trigger, strpos(trigger, ': ') + 2)) as file,
           to_char(started_at at time zone 'Asia/Kolkata', 'DD-Mon-YYYY HH24:MI') as when, status, error,
           coalesce(result -> 'copies', '[]'::jsonb) as copies, (result ->> 'pages')::int as pages,
           coalesce(result -> 'given', '[]'::jsonb) as given, ${seesUploader(me, sql`r.uploaded_by`)} as mine
    from flow_run r where flow = 'read-scan' and ${seesRun(me, sql`r`)} order by started_at desc limit ${5 * n}`;
  const ids = [...new Set(runs.flatMap((r) => [...r.copies.flatMap((c) => (c.child_id ? [c.child_id] : [])), ...r.given.map((g) => g.child_id)]))];
  const kids = new Map(
    (ids.length ? await sql<{ id: string; section: string; roll_no: string }[]>`
      select id, section, roll_no from child where id = any(${ids}::uuid[])` : []).map((k) => [k.id, k]),
  );
  const captures = [...new Set(runs.flatMap((r) => r.copies.flatMap((c) => (c.capture_id ? [c.capture_id] : []))))];
  const seenCaptures = new Set(
    (captures.length ? await sql<{ id: string }[]>`
      select id::text from unnest(${captures}::uuid[]) as k(id) where ${seesCapture(me, sql`k.id`)}` : []).map((c) => c.id),
  );
  // a copy read is seen by whoever sees its paper; one not read, by whoever sees the file's own uploader
  const shown = (r: Run, c: Copy) => (c.capture_id ? seenCaptures.has(c.capture_id) : r.mine);
  const standing = new Map<string, { engine: number; person: number; waiting: number }>();
  for (const s of captures.length ? await sql<{ capture_id: string; engine: number; person: number; waiting: number }[]>`
      select r.capture_id, count(*) filter (where a.standing = 'engine')::int as engine,
             count(*) filter (where a.standing = 'person')::int as person,
             count(*) filter (where a.standing = 'waiting')::int as waiting
      from answer_standing a join item_result r on r.id = a.item_result_id
      where r.capture_id = any(${captures}::uuid[]) group by r.capture_id` : [])
    standing.set(s.capture_id, s);
  return byFile(runs)
    .slice(0, n)
    .map(({ run: r, others }) => {
      // what the file came to, of the copies this person sees: a file holding another class's copy counts only theirs
      const seen = r.copies.filter((c) => shown(r, c));
      const read = seen.filter((c) => !c.skipped);
      const counted = seen.flatMap((c) => (c.capture_id ? [standing.get(c.capture_id) ?? { engine: 0, person: 0, waiting: 0 }] : []));
      // a page with no code: said by its number (`copies.read`'s no_code), or, on a run read before it was kept, the
      // pages of a copy not read for want of one
      const given = new Map(r.given.map((g) => [g.page, g.child_id]));
      const noCode = r.copies
        .flatMap((c) => c.no_code ?? (c.skipped && c.code === "?" ? c.pages : []))
        .filter((n) => !given.has(n))
        .sort((a, b) => a - b);
      const rollOf = (id: string) => {
        const k = kids.get(id);
        return k ? `${k.section} · roll ${k.roll_no}` : "a child";
      };
      const owners = r.copies
        .filter((c) => c.child_id && c.by_code !== false && !c.no_code?.length && shown(r, c))
        .map((c) => ({ id: c.child_id!, who: rollOf(c.child_id!), short: Boolean(c.missing?.length) }))
        .sort((a, b) => Number(b.short) - Number(a.short));
      const lines = r.copies.flatMap((c): ScanLine[] => {
        const k = c.child_id ? kids.get(c.child_id) : undefined;
        if (!shown(r, c)) return [];
        const who = k ? `${k.section} · roll ${k.roll_no}` : `Copy ${c.copy} (${pagesSaid(c.pages)})`;
        if (c.skipped) return [{ who, said: `not read — ${c.why ?? "no reason given"}` }];
        return (c.lacks ?? []).map((said) => ({ who, said }));
      });
      return {
        id: r.id,
        file: r.file || "a scan",
        when: r.when,
        status: r.status,
        error: r.error,
        read: read.length,
        answers: read.reduce((n, c) => n + (c.answers ?? 0), 0),
        lines,
        pages: r.pages,
        copies: seen.length,
        children: new Set(seen.flatMap((c) => (c.child_id ? [c.child_id] : []))).size,
        engine: counted.reduce((n, c) => n + c.engine, 0),
        person: counted.reduce((n, c) => n + c.person, 0),
        waiting: counted.reduce((n, c) => n + c.waiting, 0),
        noCode,
        owners,
        given: [...given].filter(([, id]) => r.mine || isMine(scope, kids.get(id)?.section ?? null)).map(([page, id]) => ({ page, who: rollOf(id) })),
        attempts: others.map((o) => ({ when: o.when, status: o.status, error: o.error })),
      };
    });
}
