import { sql } from "./db";
import { engineGet } from "./engine";
import { isoWeek } from "./week";

// Make papers (goals/m1-make-papers.yaml): each child's own paper. The engine proposes each home paper from the
// child's map (`w2_print/focus_paper.py`) and makes any paper a teacher asks for; this reads what it proposes.

/** A child the engine can propose a home paper for: a skill on their map that is red, amber or green, and no
 *  home paper yet this week. A child with fewer than three answers everywhere has nothing to go on. */
const PROPOSABLE = ["patterned_error", "emerging", "practising", "secure", "stretch_ready"];

export type ClassHome = { section: string; band: string; children: number; proposed: number; approved: number };

export async function homeByClass(week = isoWeek()): Promise<ClassHome[]> {
  return sql<ClassHome[]>`
    select c.section, min(c.band) as band, count(*)::int as children,
           count(*) filter (where h.qr_code is null and exists (
             select 1 from child_skill_state s where s.child_id = c.id and s.state = any(${PROPOSABLE})))::int as proposed,
           count(h.qr_code)::int as approved
    from child c
    left join lateral (select qr_code from sheet_instance si
                       where si.child_id = c.id and si.kind = 'focus' and si.week = ${week} limit 1) h on true
    where c.active
    group by c.section
    order by min(c.band), c.section`;
}

/** How many children the engine proposes a home paper for this week, across the school — as Today counts them. */
export async function proposedHomePapers(week = isoWeek()): Promise<number> {
  return (await homeByClass(week)).reduce((n, c) => n + c.proposed, 0);
}

export type Proposal = {
  areas: { name: string; level: string; why: string; questions: unknown[] }[];
  approved: { qr: string; approved_by: string } | null;
};

export type ClassChild = { id: string; roll_no: string; first_name: string; proposal: Proposal };

/** A class's children with the home paper the engine proposes for each, or the one already approved. Names come
 *  through pii.read_child, which logs who asked. */
export async function classHome(section: string, actor: string, week = isoWeek()): Promise<ClassChild[]> {
  const children = await sql<{ id: string; roll_no: string; first_name: string }[]>`
    select c.id, c.roll_no, p.first_name from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.active and c.section = ${section}
    order by coalesce(nullif(regexp_replace(c.roll_no, '\\D', '', 'g'), '')::int, 9999), c.roll_no`;
  return Promise.all(
    children.map(async (c) => {
      const res = await engineGet(`/child/${c.id}/focus?week=${week}`);
      const proposal = res.ok ? ((await res.json()) as Proposal) : { areas: [], approved: null };
      return { ...c, proposal };
    }),
  );
}

/** One child, by id, with their class — for a paper a teacher chooses. */
export async function oneChild(id: string, actor: string) {
  const [c] = await sql<{ id: string; section: string; band: string; first_name: string }[]>`
    select c.id, c.section, c.band, p.first_name from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.id = ${id}::uuid and c.active`;
  return c;
}
