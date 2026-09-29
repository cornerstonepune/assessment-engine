import { sql } from "./db";

// A child's report card (goals/u6-report-card.yaml): their skill map and the facts it rests on. Every number here is
// read from signed-off answers on readings nobody has superseded; nothing is estimated.

export type MapNode = {
  code: string;
  name: string;
  objective: string;
  rung_code: string;
  band: string;
  ladder_order: number | null;
  lane: string;
  lane_name: string;
  state: string | null;
  right: number;
  wrong: number;
  wrong_working: number;
  blank: number;
};

const WEAKEST_FIRST = [
  "patterned_error",
  "emerging",
  "practising",
  "secure",
  "stretch_ready",
  "not_enough_yet",
];

/** The taught skill sets of the child's grade and the grades either side, and any other a signed-off answer of theirs
 *  landed on — each with the graph's state (the weakest of its skills, as the class card places a child) and the
 *  child's answers on it in the three signals: right, wrong (with or without working), blank. A skill set's lane is the
 *  registry skill it practises; its place in the lane is the school's ladder. */
export async function skillMap(id: string): Promise<MapNode[]> {
  return sql<MapNode[]>`
    with me as (select band from child where id = ${id}::uuid),
    st as (
      select s.rung_code,
             (array_agg(s.state order by array_position(${WEAKEST_FIRST}::text[], s.state)))[1] as state
      from child_skill_state s join rung r on r.code = s.rung_code
      where s.child_id = ${id}::uuid and s.skill_code = any(r.skill_codes) and s.n_events > 0
      group by s.rung_code),
    sig as (
      select e.placed_rung as rung_code,
             count(*) filter (where e.correct)::int as right,
             count(*) filter (where e.correct = false and coalesce(ir.working_shown, 'none') = 'none')::int as wrong,
             count(*) filter (where e.correct = false and coalesce(ir.working_shown, 'none') <> 'none')::int as wrong_working,
             count(*) filter (where e.correct is null)::int as blank
      from evidence_placed e
      left join item_result ir on ir.id = e.item_result_id
      left join capture c on c.id = ir.capture_id
      where e.child_id = ${id}::uuid and e.confirmed_by is not null and (c.id is null or c.superseded_by is null)
      group by e.placed_rung)
    select ss.code, ss.name, coalesce(ss.learning_objective, '') as objective, r.code as rung_code,
           left(r.band, 2) as band, r.ladder_order, r.skill_codes[1] as lane, coalesce(k.name, r.skill_codes[1]) as lane_name,
           st.state, coalesce(sig.right, 0) as right, coalesce(sig.wrong, 0) as wrong,
           coalesce(sig.wrong_working, 0) as wrong_working, coalesce(sig.blank, 0) as blank
    from skill_set ss
    join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code and t.taught
    join rung r on r.tenant_id = ss.tenant_id and r.code = ss.rung_code
    left join st on st.rung_code = r.code
    left join sig on sig.rung_code = r.code
    left join lateral (select name from skill where code = r.skill_codes[1] limit 1) k on true
    where ss.status is distinct from 'retired'
      and (abs(substring(r.band from 2 for 1)::int - substring((select band from me) from 2 for 1)::int) <= 1
           or st.rung_code is not null or sig.rung_code is not null)
    order by r.skill_codes[1], left(r.band, 2), r.ladder_order nulls last, ss.code`;
}

export type Coverage = {
  papers: number;
  answers: number;
  signed: number;
  first: string | null;
  last: string | null;
};

/** What the card rests on: the child's papers read and not superseded, their answers, how many a person signed off,
 *  and the dates of the signed-off answers. */
export async function coverage(id: string): Promise<Coverage> {
  const [c] = await sql<Coverage[]>`
    select count(distinct c.id)::int as papers, count(ir.id)::int as answers,
           count(ir.id) filter (where ir.state = 'confirmed')::int as signed,
           (select min(observed_at)::text from evidence_placed where child_id = ${id}::uuid and confirmed_by is not null) as first,
           (select max(observed_at)::text from evidence_placed where child_id = ${id}::uuid and confirmed_by is not null) as last
    from capture c
    join sheet_instance si on si.id = c.sheet_instance_id
    join item_result ir on ir.capture_id = c.id
    where si.child_id = ${id}::uuid and c.superseded_by is null`;
  return c;
}

/** How far the map reaches: every skill set of the child's grade, and in each lane the one step before it and the one
 *  step after it on the ladder — where the child is, what it stands on and what comes next — and any skill set the
 *  child has answers on, wherever it sits. */
export function around(nodes: MapNode[], band: string): MapNode[] {
  const g = (n: MapNode) => Number(n.band.slice(1));
  const me = Number(band.slice(1));
  const answered = (n: MapNode) =>
    n.state !== null || n.right + n.wrong + n.wrong_working + n.blank > 0;
  const onLadder = (n: MapNode, grade: number) =>
    nodes.filter(
      (m) => m.lane === n.lane && m.ladder_order !== null && g(m) === grade,
    );
  return nodes.filter((n) => {
    if (g(n) === me || answered(n)) return true;
    if (g(n) === me - 1) return onLadder(n, me - 1).at(-1)?.code === n.code;
    if (g(n) === me + 1) return onLadder(n, me + 1)[0]?.code === n.code;
    return false;
  });
}

export type Placed = MapNode & { x: number; y: number };
export type Edge = { from: string; to: string };

/** Where each skill set sits on the map: a column per grade, a row per lane; within a lane and grade the ladder's
 *  order. An arrow joins each skill set on the ladder to the next one up its lane — the order the school teaches them
 *  in (`rung.ladder_order`); there is no table of prerequisites, so no other edge is drawn. */
export function layout(nodes: MapNode[]) {
  const bands = [...new Set(nodes.map((n) => n.band))].sort();
  const lanes = [...new Set(nodes.map((n) => n.lane))];
  const col = (b: string) => bands.indexOf(b);
  const slots = Object.fromEntries(bands.map((b) => [b, 0]));
  for (const lane of lanes)
    for (const b of bands)
      slots[b] = Math.max(
        slots[b],
        nodes.filter((n) => n.lane === lane && n.band === b).length,
      );
  const start = bands.map((_, i) =>
    bands.slice(0, i).reduce((s, b) => s + slots[b], 0),
  );
  const placed: Placed[] = [];
  const edges: Edge[] = [];
  lanes.forEach((lane, y) => {
    const mine = nodes.filter((n) => n.lane === lane);
    bands.forEach((b) =>
      mine
        .filter((n) => n.band === b)
        .forEach((n, k) => placed.push({ ...n, x: start[col(b)] + k, y })),
    );
    // only the ladder's own order: a skill set with no place on it (missing digits, equality) is drawn, never joined
    const ladder = mine.filter((n) => n.ladder_order !== null);
    for (let k = 1; k < ladder.length; k++)
      edges.push({ from: ladder[k - 1].code, to: ladder[k].code });
  });
  const columns = bands.map((b, i) => ({
    band: b,
    from: start[i],
    width: slots[b],
  }));
  return {
    placed,
    edges,
    lanes: lanes.map((l) => nodes.find((n) => n.lane === l)!.lane_name),
    columns,
  };
}
