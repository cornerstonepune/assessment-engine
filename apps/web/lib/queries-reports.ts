import { sql } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";

// Parent reports by where they stand (goals/ui4b1-child-by-topic.yaml): a child's newest report written for a parent,
// approved or a draft, out of date once answers were signed off after it was written; and every child whose report
// waits on a person, in one list. A child none of whose answers is signed off has nothing to report — the engine
// writes no report from nothing (`parent_facts.SIGNED`) — so waits on no one. Names through pii.read_child, which logs
// who asked.
export type Note = { approved: boolean; out_of_date: boolean; written: string; approved_by: string | null };
export type ReportState = { note: Note | null; signed: boolean };

/** The newest report of the child a fragment names (a column or a value), as one json value. */
const newest = (child: ReturnType<typeof sql>) => sql`
  (select jsonb_build_object(
            'approved', n.approved_by is not null,
            'approved_by', n.approved_by,
            'written', n.created_at::date::text,
            'out_of_date', exists (select 1 from evidence_event e where e.child_id = n.child_id
                                    and e.confirmed_by is not null and e.created_at > n.created_at))
     from parent_note n where n.child_id = ${child} and n.body like '{"facts"%'
    order by n.created_at desc limit 1)`;

/** Whether an educator has signed off any answer of the child's, read as the engine's `parent_facts.SIGNED` reads it. */
const signed = (child: ReturnType<typeof sql>) => sql`
  exists (select 1 from answer_placed a
          left join item_result ir on ir.id = a.item_result_id
          left join capture k on k.id = ir.capture_id
          where a.child_id = ${child} and a.confirmed_by is not null and (k.id is null or k.superseded_by is null))`;

/** A child's report state, `ReportState`, as one json value: the one way every page reads it. */
export const reportState = (child: ReturnType<typeof sql>) => sql`jsonb_build_object('note', ${newest(child)}, 'signed', ${signed(child)})`;

export async function reportOf(id: string): Promise<ReportState> {
  const [row] = await sql<{ report: ReportState }[]>`select ${reportState(sql`${id}::uuid`)} as report`;
  return row?.report ?? { note: null, signed: false };
}

export type ReportRow = { child_id: string; first_name: string; band: string; section: string; roll_no: string; report: ReportState };

/** Every child whose report waits on a person: out of date first, then written and not approved, then not written
 *  though there are answers to write it from. */
export async function reportsWaiting(actor: string, scope: Scope = EVERY_CLASS): Promise<ReportRow[]> {
  const rows = await sql<ReportRow[]>`
    select c.id as child_id, p.first_name, c.band, c.section, c.roll_no, ${reportState(sql`c.id`)} as report
    from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.active and ${inScope(scope, sql`c.section`)}
    order by c.band, c.section, roll_order(c.roll_no), c.roll_no`;
  return rows.filter((r) => reportRank(r.report) < 3).sort((a, b) => reportRank(a.report) - reportRank(b.report));
}

/** What needs a person first: out of date, then written and not approved, then not written though it could be; an
 *  approved report and a child with nothing to report need no one. */
export const reportRank = ({ note, signed }: ReportState) => (!note ? (signed ? 2 : 3) : note.out_of_date ? 0 : note.approved ? 3 : 1);

/** Whether a report waits on someone: written, and out of date or not yet approved. Nothing written is no one's work
 *  until there are answers to write it from, and then the Parent reports page lists it. */
export const reportWaits = ({ note }: ReportState) => !!note && (note.out_of_date || !note.approved);

/** A report's state in the school's words: a sentence (`words`), and a pill's word for a list (`short`). */
export function reportWords({ note: r, signed }: ReportState): { words: string; tone: "terracotta" | "bamboo" | "neem" | "monsoon"; short: string } {
  if (!r && !signed) return { words: "Nothing to report yet: none of their answers is signed off", tone: "monsoon", short: "nothing yet" };
  if (!r) return { words: "Not written yet", tone: "monsoon", short: "to write" };
  if (r.out_of_date) return { words: "Out of date: answers were signed off after it was written", tone: "terracotta", short: "out of date" };
  if (!r.approved) return { words: "Written, waiting for a person to approve it", tone: "bamboo", short: "to approve" };
  return { words: "Approved", tone: "neem", short: "approved" };
}
