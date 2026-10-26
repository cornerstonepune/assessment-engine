import { sql } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";

// Today — everything waiting on a teacher (goals/u1-today.yaml). Each count is the one the page it opens shows:
// the answers queue and the papers to sign off are read through that page's own query, not a second copy of it.

export type Pack = { section: string; band: string; week: string; kind: string; n: number };
/** A child whose parent report is written and waits for a person to approve it. */
export type Report = { child_id: string; band: string; section: string; roll_no: string };
/** Class papers the engine made that no teacher has approved for print, pack by pack. */
export async function classPacksWaiting(scope: Scope = EVERY_CLASS): Promise<Pack[]> {
  return sql<Pack[]>`
      select c.section, class_band(c.tenant_id, c.section) as band, si.week, si.kind, count(*)::int as n
      from sheet_instance si join child c on c.id = si.child_id
      where si.print_status = 'new' and si.kind in ('practice', 'assessment') and ${inScope(scope, sql`c.section`)}
      group by c.tenant_id, c.section, si.week, si.kind
      order by si.week desc, c.section, si.kind`;
}

/** Each active child's newest parent report, where it is written and no one has approved it yet. */
export async function reportsWaiting(scope: Scope = EVERY_CLASS): Promise<Report[]> {
  return sql<Report[]>`
    select c.id as child_id, c.band, c.section, c.roll_no
    from child c
    join lateral (select n.approved_by from parent_note n where n.child_id = c.id and n.body like '{"facts"%'
                  order by n.created_at desc limit 1) n on true
    where c.active and n.approved_by is null and ${inScope(scope, sql`c.section`)}
    order by grade_ord(c.tenant_id, c.band), c.section, roll_order(c.roll_no), c.roll_no`;
}

// Whether the queue shrinks as the reader earns trust (goals/ny2-the-queue-shrinks.yaml). Nimish, 2026-10-10: "the number
// of data points that we then need to validate becomes lower".
export type Week = { week: string; read: number; alone: number; person: number; waiting: number };
export type Trust = { trusted: number; kinds: number; nearest: { fmt: string; to_trust: number } | null };

/** The answers read each ISO week, newest first, by where each stands (`answer_standing`, the one definition): settled
 *  by the engine alone, checked by a person, still waiting. The last eight weeks: two months is the trend. In the
 *  person's classes, as the lines above it on Today count (goals/ux8a-numbers-true.yaml). */
export async function queueByWeek(scope: Scope = EVERY_CLASS): Promise<Week[]> {
  return sql<Week[]>`
    select to_char(c.created_at, 'IYYY-"W"IW') as week, count(*)::int as read,
           count(*) filter (where s.standing = 'engine')::int as alone,
           count(*) filter (where s.standing = 'person')::int as person,
           count(*) filter (where s.standing = 'waiting')::int as waiting
    from answer_standing s join item_result r on r.id = s.item_result_id join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id left join child ch on ch.id = si.child_id
    where ${inScope(scope, sql`coalesce(si.section, ch.section)`)}
    group by 1 order by 1 desc limit 8`;
}

/** How near the reader is to trust, by the one rule (`kind_trust`): the kinds trusted of those it has stood behind a
 *  reading of, and the nearest not yet trusted — the fewest right checks still needed. */
export async function trustNow(): Promise<Trust> {
  const rows = await sql<{ fmt: string; trusted: boolean; to_trust: number }[]>`
    select fmt, trusted, checks_to_trust as to_trust from kind_trust order by checks_to_trust, fmt`;
  const near = rows.find((r) => !r.trusted);
  return { trusted: rows.filter((r) => r.trusted).length, kinds: rows.length, nearest: near ? { fmt: near.fmt, to_trust: near.to_trust } : null };
}
