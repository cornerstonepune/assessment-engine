import { sql } from "./db";
import { asksWaiting, skillsWaiting, topicsOff } from "./queries-people";
import { checkQueue, papersToApprove } from "./queries-read";
import { proposedHomePapers } from "./queries-make";

// Today — everything waiting on a teacher (goals/u1-today.yaml). Each count is the one the page it opens shows:
// the answers queue and the papers to sign off are read through that page's own query, not a second copy of it.

export type Pack = { section: string; week: string; kind: string; n: number };
export type Waiting = {
  answers: number; // answers left in the checking queue (spot-checks apart), as /capture/check counts them
  papers: number; // papers read with an answer not yet signed off, as /capture counts them
  packs: Pack[]; // class papers the engine proposed that no teacher has approved for print
  nextPapers: number; // children the engine proposes a home paper for this week, as Make papers counts them
  skills: number; // skill sets awaiting approval, taught or not: one is approved before its topic is on
  topics: number; // topics not taught yet, as Curriculum lists them to switch on
  asks: { for_role: string; n: number }[]; // the questions drafted for a person, still waiting, by whose they are
};

/** Class papers the engine made that no teacher has approved for print, pack by pack. */
export async function classPacksWaiting(): Promise<Pack[]> {
  return sql<Pack[]>`
      select c.section, si.week, si.kind, count(*)::int as n
      from sheet_instance si join child c on c.id = si.child_id
      where si.print_status = 'new' and si.kind in ('practice', 'assessment')
      group by c.section, si.week, si.kind
      order by si.week desc, c.section, si.kind`;
}

export async function waiting(actor: string): Promise<Waiting> {
  const [queue, read, packs, next, skills, topics, asks] = await Promise.all([
    checkQueue(),
    papersToApprove(actor),
    classPacksWaiting(),
    proposedHomePapers(),
    skillsWaiting(),
    topicsOff(),
    asksWaiting(),
  ]);
  return {
    answers: queue.filter((e) => !e.spot).length,
    papers: read.filter((p) => p.n_results > 0 && p.n_candidate > 0).length,
    packs,
    nextPapers: next,
    skills,
    topics,
    asks,
  };
}

// Whether the queue shrinks as the reader earns trust (goals/ny2-the-queue-shrinks.yaml). Nimish, 2026-10-10: "the number
// of data points that we then need to validate becomes lower".
export type Week = { week: string; read: number; alone: number; person: number; waiting: number };
export type Trust = { trusted: number; kinds: number; nearest: { fmt: string; to_trust: number } | null };

/** The answers read each ISO week, newest first, by where each stands (`answer_standing`, the one definition): settled
 *  by the engine alone, checked by a person, still waiting. The last eight weeks: two months is the trend. */
export async function queueByWeek(): Promise<Week[]> {
  return sql<Week[]>`
    select to_char(c.created_at, 'IYYY-"W"IW') as week, count(*)::int as read,
           count(*) filter (where s.standing = 'engine')::int as alone,
           count(*) filter (where s.standing = 'person')::int as person,
           count(*) filter (where s.standing = 'waiting')::int as waiting
    from answer_standing s join item_result r on r.id = s.item_result_id join capture c on c.id = r.capture_id
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
