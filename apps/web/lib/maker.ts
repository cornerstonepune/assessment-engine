import { engineSend } from "./engine";
import { readArea, type Area } from "./next-paper";

// The maker (goals/m3-the-maker.yaml): papers for any children of one class at once. The engine draws, checks and
// prints them (`w2_print/maker.py`); this reads the educator's choices from the form or the address and asks it.

/** What a paper is, in the school's words: its kind, its name, and one line on what it is for. */
export const KINDS: [string, string, string][] = [
  ["practice", "Class practice", "Sat in class, to practise."],
  ["assessment", "Class assessment", "Sat in class, to see what is secure."],
  ["focus", "Home assessment", "Sent home. One a child a week."],
];

/** The three ways to make them. Nimish, 2026-09-30: "the same skill paper for multiple children", "individual papers
 *  for each child", "choose the right skill and the grade level, and then choose the children and generate different
 *  questions". */
export const WAYS: [string, string, string][] = [
  ["each", "Same skill, different questions", "You choose the skill and level; each child gets questions of their own, no two sharing one."],
  ["same", "One paper for all", "You choose the skill and level; every child gets the same questions."],
  ["own", "Each child's own next step", "The engine picks each child's skill and level from their checked answers; you can change any child."],
];

/** A changed child's paper is as long as a home paper. */
export const OWN_N = 12;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export type Batch = {
  section: string;
  week: string;
  kind: string;
  way: string;
  children: string[];
  areas: Area[];
  changed: Record<string, Area[]>;
};

/** The batch a form or an address describes — `class`, `kind`, `way`, the children `c`, the areas as whole `a`
 *  (skill~level~n) or as the form's lines `s` (skill~level) and `n`, and each changed child `x` (child~skill~level)
 *  — or null while the class, kind or way is missing. */
export function readBatch(get: (k: string) => string[], week: string): Batch | null {
  const section = get("class")[0] ?? "";
  const kind = get("kind")[0] ?? "";
  const way = get("way")[0] ?? "";
  if (!section || !KINDS.some(([k]) => k === kind) || !WAYS.some(([w]) => w === way)) return null;
  const n = get("n");
  const areas = [...get("a").map(readArea), ...get("s").map((v, i) => (v && n[i] ? readArea(`${v}~${n[i]}`) : null))];
  const changed: Record<string, Area[]> = {};
  for (const x of get("x")) {
    const [child, skill_set, level] = x.split("~");
    if (UUID.test(child ?? "") && skill_set && level) changed[child] = [{ skill_set, level, n: OWN_N }];
  }
  return {
    section,
    week,
    kind,
    way,
    children: get("c").filter((c) => UUID.test(c)),
    areas: way === "own" ? [] : areas.filter((a): a is Area => !!a),
    changed: way === "own" ? changed : {},
  };
}

/** The batch as the address carries it, so a page, a form and a redirect all say the same thing. */
export function batchQuery(b: Batch): URLSearchParams {
  const q = new URLSearchParams({ class: b.section, kind: b.kind, way: b.way, picked: "1" });
  for (const c of b.children) q.append("c", c);
  for (const a of b.areas) q.append("a", `${a.skill_set}~${a.level}~${a.n}`);
  for (const [c, [a]] of Object.entries(b.changed)) q.append("x", `${c}~${a.skill_set}~${a.level}`);
  return q;
}

export type PlannedPaper = {
  child_id: string;
  roll_no: string;
  chosen: "graph" | "educator";
  n: number;
  areas: { skill_set: string; name: string; level: string; why: string; questions: { item_key: string; text: string }[] }[];
};
export type MakerPlan = { papers: PlannedPaper[]; refused: { child_id: string; roll_no: string; why: string }[] };

/** What the papers would hold, child by child, and each child whose paper cannot be made with why; or, when the
 *  batch cannot be made at all, the engine's words. Nothing is written. */
export async function planBatch(b: Batch): Promise<{ plan: MakerPlan } | { refused: string }> {
  const res = await engineSend("/papers/plan", b);
  if (res.ok) return { plan: (await res.json()) as MakerPlan };
  const detail = ((await res.json().catch(() => ({}))) as { detail?: unknown }).detail;
  return { refused: typeof detail === "string" ? detail : `The engine refused (${res.status}).` };
}
