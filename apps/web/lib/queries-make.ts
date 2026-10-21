import { sql } from "./db";
import { EVERY_CLASS, inScope, type Scope } from "./scope";
import { engineGet } from "./engine";
import { isoWeek } from "./week";

// Make papers (goals/m1-make-papers.yaml): each child's own paper. The engine proposes each home paper from the
// child's map (`w2_print/focus_paper.py`) and makes any paper a teacher asks for; this reads what it proposes.

/** How many questions a home paper holds — the `assemble.items_per_sheet` row the engine makes them by — for the
 *  maker's first line to start at; null when there is no such row, and the educator says. */
export async function homeLength(): Promise<number | null> {
  const [row] = await sql<{ n: number }[]>`select value::int as n from config where key = 'assemble.items_per_sheet'`;
  return row?.n ?? null;
}

export type ClassHome = { section: string; band: string; children: number; proposed: number; approved: number };

export async function homeByClass(week = isoWeek(), scope: Scope = EVERY_CLASS): Promise<ClassHome[]> {
  return sql<ClassHome[]>`
    -- a class's grade is the database's one rule (class_band), as on every page (goals/ux2-one-count-one-thing.yaml)
    select c.section, class_band(c.tenant_id, c.section) as band, count(*)::int as children,
           count(*) filter (where h.qr_code is null and exists (
             -- a child the engine can propose a home paper for: a skill on their map in a state with enough answers to
             -- say (red, amber or green), and no home paper yet this week
             select 1 from child_skill_state s join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
             where s.child_id = c.id and cs.enough))::int as proposed,
           count(h.qr_code)::int as approved
    from child c
    -- the week's home assessment is the newest; one made again is still one child's (goals/home-assessment-remake.yaml)
    left join lateral (select qr_code from sheet_instance si
                       where si.child_id = c.id and si.kind = 'focus' and si.week = ${week}
                       order by si.created_at desc limit 1) h on true
    where c.active and ${inScope(scope, sql`c.section`)}
    group by c.tenant_id, c.section
    order by class_band(c.tenant_id, c.section), c.section`;
}

/** How many children the engine proposes a home paper for this week, in the classes a person sees — as Today counts
 *  them. */
export async function proposedHomePapers(week = isoWeek(), scope: Scope = EVERY_CLASS): Promise<number> {
  return (await homeByClass(week, scope)).reduce((n, c) => n + c.proposed, 0);
}

export type Proposal = {
  areas: { name: string; level: string; why: string; questions: unknown[] }[];
  approved: { qr: string; approved_by: string; replaced: string[] } | null;
};

export type ClassChild = { id: string; roll_no: string; first_name: string; proposal: Proposal };

/** A class's children with the home paper the engine proposes for each, or the one already approved. Names come
 *  through pii.read_child, which logs who asked. */
export async function classHome(section: string, actor: string, week = isoWeek()): Promise<ClassChild[]> {
  const children = await sql<{ id: string; roll_no: string; first_name: string }[]>`
    select c.id, c.roll_no, p.first_name from child c, lateral pii.read_child(c.id, ${actor}) p
    where c.active and c.section = ${section}
    order by roll_order(c.roll_no), c.roll_no`;
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
