import { sql } from "./db";
import { DIFFICULTIES } from "./queries";

// What each colour means, and the check that places a child the colours cannot yet say anything about
// (goals/u11-colours-said.yaml). Nimish, 2026-09-30: "The clarity of what each of the colors means has not been very
// clearly mentioned. How do we classify students across different tiers?" The numbers are the rows
// `rebuild_child_skill_state` decides a state by, read here so the words on the page are always the rule in force.

export type ColourRules = {
  /** Answers a skill needs before it has a colour at all (`state.min_events`). */
  minAnswers: number;
  /** Papers a skill must be seen on before it is green (`state.min_observers`). */
  minPapers: number;
  /** The share right from which a skill is green (`next_sheet.promote_at`), and under which it is red. */
  promote: number;
  demote: number;
  /** The level each grade starts at when a child has too little work to go on (`prescribe.band_default`). */
  levels: Record<string, string>;
  /** Questions in a check that places a child: enough for the colour to be decided, and for the green share to show
   *  (five for four in five). */
  checkSize: number;
};

export async function colourRules(): Promise<ColourRules> {
  const [r] = await sql<{ min_events: number; min_obs: number; promote: number; demote: number; levels: Record<string, string> }[]>`
    select coalesce((select value from threshold where key = 'state.min_events'), 3)::float as min_events,
           coalesce((select value from threshold where key = 'state.min_observers'), 2)::float as min_obs,
           coalesce((select value from threshold where key = 'next_sheet.promote_at'), 0.8)::float as promote,
           coalesce((select value from threshold where key = 'next_sheet.demote_below'), 0.5)::float as demote,
           coalesce((select value from config where key = 'prescribe.band_default'), '{}'::jsonb) as levels`;
  // the fewest answers in which the green share can show: 1 wrong in 5 is 80%; rounded before the ceiling, as 1/(1−0.8)
  // is 5.000000000000001 in floating point
  const forShare = Math.ceil(Number((1 / (1 - r.promote)).toFixed(6)));
  return {
    minAnswers: r.min_events,
    minPapers: r.min_obs,
    promote: r.promote,
    demote: r.demote,
    levels: r.levels,
    checkSize: Math.max(r.min_events, forShare),
  };
}

/** The level a check on a skill is set at for a grade: the grade's starting level where the skill has it, else the
 *  skill's easiest. */
export function checkLevel(rules: ColourRules, band: string, defined: string[]): string {
  const start = rules.levels[band];
  return start && defined.includes(start) ? start : (DIFFICULTIES.find((l) => defined.includes(l)) ?? start ?? DIFFICULTIES[0]);
}

/** Where the maker opens with a check already chosen: a class assessment, the same skill and level for each child,
 *  different questions each (goals/m3-the-maker.yaml). */
export function checkHref(section: string, children: string[], skillSet: string, level: string, n: number): string {
  const q = new URLSearchParams({ class: section, picked: "1", of: section, kind: "assessment", way: "each" });
  for (const c of children) q.append("c", c);
  q.append("a", `${skillSet}~${level}~${n}`);
  return `/papers/make?${q}`;
}
