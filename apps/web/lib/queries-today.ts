import { sql } from "./db";
import { checkQueue, papersToApprove } from "./queries-read";
import { NEEDS_WORK } from "./rag";

// Today — everything waiting on a teacher (goals/u1-today.yaml). Each count is the one the page it opens shows:
// the answers queue and the papers to sign off are read through that page's own query, not a second copy of it.

export type Pack = { section: string; week: string; kind: string; n: number };
export type Waiting = {
  answers: number; // answers left in the checking queue (spot-checks apart), as /capture/check counts them
  papers: number; // papers read with an answer not yet signed off, as /capture counts them
  packs: Pack[]; // class papers the engine proposed that no teacher has approved for print
  nextPapers: number; // children with a red or amber skill and no next paper made this week
  skills: number; // skill sets awaiting approval
};

export async function waiting(actor: string): Promise<Waiting> {
  const [queue, read, packs, [{ next }], [{ skills }]] = await Promise.all([
    checkQueue(),
    papersToApprove(actor),
    sql<Pack[]>`
      select c.section, si.week, si.kind, count(*)::int as n
      from sheet_instance si join child c on c.id = si.child_id
      where si.print_status = 'new' and si.kind in ('practice', 'assessment')
      group by c.section, si.week, si.kind
      order by si.week desc, c.section, si.kind`,
    sql<{ next: number }[]>`
      select count(distinct s.child_id)::int as next
      from child_skill_state s join child c on c.id = s.child_id
      where c.active and s.state = any(${NEEDS_WORK})
        and not exists (select 1 from sheet_instance si where si.child_id = s.child_id and si.kind = 'focus'
                        and si.created_at > date_trunc('week', now()))`,
    sql<{ skills: number }[]>`select count(*)::int as skills from skill_set where status <> 'ratified'`,
  ]);
  return {
    answers: queue.filter((e) => !e.spot).length,
    papers: read.filter((p) => p.n_results > 0 && p.n_candidate > 0).length,
    packs,
    nextPapers: next,
    skills,
  };
}
