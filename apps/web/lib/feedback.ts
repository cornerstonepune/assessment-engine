import { createHmac } from "node:crypto";
import { sql, TENANT_SLUG } from "./db";
import { createIssue, FROM_THE_TOOL, toolIssues } from "./github";
import { issueBody, issueTitle, KINDS, seenAs, type Note, type NoteKind, type HowOften, type Seen } from "./feedback-words";

// A note from staff, kept first and then sent to GitHub as one issue (goals/feed_report_from_the_tool.yaml). Kept
// first, so a note is never lost: GitHub not connected leaves it `saved`, GitHub refusing leaves it `failed`, and each
// later visit to the form tries the waiting ones again, oldest first (`feedback.send_per_try`), while `engine live watch`
// says how many wait. A try holds its note for a minute (`tried_at`), so two visits at once never make two issues.

/** Who wrote a note, as the row keeps it: an HMAC of their email under the site's secret. It counts a person's notes
 *  and finds their own, and names nobody. */
export function reporterMark(email: string): string {
  return createHmac("sha256", process.env.AUTH_SECRET ?? "").update(`staff_note.${email.toLowerCase()}`).digest("hex").slice(0, 32);
}

export type Limits = { perHour: number; maxChars: number; perTry: number };

export async function limits(): Promise<Limits> {
  const [row] = await sql<{ per_hour: number; max_chars: number; per_try: number }[]>`
    select (select value from threshold where key = 'feedback.max_per_hour')::int as per_hour,
           (select value from threshold where key = 'feedback.max_chars')::int as max_chars,
           (select value from threshold where key = 'feedback.send_per_try')::int as per_try`;
  return { perHour: row?.per_hour ?? 5, maxChars: row?.max_chars ?? 2000, perTry: row?.per_try ?? 5 };
}

/** True when this person has already sent `feedback.max_per_hour` notes in the last hour. */
export async function tooMany(reporter: string, perHour: number): Promise<boolean> {
  const [row] = await sql<{ n: number }[]>`
    select count(*)::int as n from staff_note where reporter = ${reporter} and created_at > now() - interval '1 hour'`;
  return (row?.n ?? 0) >= perHour;
}

export async function saveNote(n: Omit<Note, "at">, reporter: string): Promise<string> {
  const [row] = await sql<{ id: string }[]>`
    insert into staff_note (tenant_id, kind, doing, happened, how_often, route, role, classes, browser, reporter)
    select id, ${n.kind}, ${n.doing}, ${n.happened}, ${n.howOften}, ${n.route}, ${n.role}, ${n.classes}, ${n.browser},
           ${reporter}
    from tenant where slug = ${TENANT_SLUG}
    returning id`;
  return row.id;
}

type Row = {
  id: string;
  kind: NoteKind;
  doing: string;
  happened: string;
  how_often: HowOften | null;
  route: string;
  role: string;
  classes: string;
  browser: string;
  created_at: Date;
};

/** Sends one note if no other try holds it: the claim and the check are one statement, so only one try wins. */
async function send(id: string): Promise<void> {
  const [n] = await sql<Row[]>`
    update staff_note set tried_at = now()
    where id = ${id} and status <> 'sent' and (tried_at is null or tried_at < now() - interval '1 minute')
    returning id, kind, doing, happened, how_often, route, role, classes, browser, created_at`;
  if (!n) return;
  const note: Note = { ...n, howOften: n.how_often, at: new Date(n.created_at) };
  const made = await createIssue(issueTitle(note), issueBody(note), [FROM_THE_TOOL, KINDS[n.kind].label]);
  if (typeof made === "object") {
    await sql`update staff_note set status = 'sent', issue_number = ${made.number} where id = ${id}`;
  } else if (made === "failed") {
    await sql`update staff_note set status = 'failed' where id = ${id}`;
  }
  // "not connected": the note stays `saved`, and the health check says so
}

/** This note first, then the oldest others still waiting, `feedback.send_per_try` in all. */
export async function sendWaiting(first?: string): Promise<void> {
  const { perTry } = await limits();
  const rows = await sql<{ id: string }[]>`
    select id from staff_note where status <> 'sent' order by (id = ${first ?? null}::uuid) desc nulls last, created_at
    limit ${perTry}`;
  for (const r of rows) await send(r.id);
}

export type MyReport = { id: string; kind: NoteKind; title: string; created_at: Date; seen: Seen };

/** This person's own notes, newest first, as received, taken up or done. */
export async function myReports(reporter: string): Promise<MyReport[]> {
  const rows = await sql<{ id: string; kind: NoteKind; doing: string; happened: string; created_at: Date; issue_number: number | null }[]>`
    select id, kind, doing, happened, created_at, issue_number from staff_note
    where reporter = ${reporter} order by created_at desc limit 50`;
  const issues = rows.some((r) => r.issue_number) ? await toolIssues() : new Map();
  return rows.map((r) => ({
    id: r.id,
    kind: r.kind,
    title: issueTitle(r).replace(/​/g, ""),
    created_at: r.created_at,
    seen: seenAs(r.issue_number ? issues.get(r.issue_number) : undefined),
  }));
}
