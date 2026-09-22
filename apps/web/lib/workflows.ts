import map from "../../../workflows.json";
import { sql } from "@/lib/db";

// The map of the engine (`workflows.json` at the top of the repository), read as it is committed — the
// same file `packages/engine/tests/test_layout.py` holds the code to, so this page cannot draw a step,
// a file or a connection the code does not have.
export type Step = {
  code: string;
  workflow: string;
  name: string;
  does: string;
  who: string;
  built: "live" | "partly" | "not built";
  takes: string[];
  gives: string[];
  files: string[];
  commands: string[];
  screens: string[];
  subject: { any: boolean; note: string };
};
export type Workflow = { code: string; name: string; folder: string | null; does: string; steps: string[] };
export type Shared = { code: string; name: string; does: string; folder: string; files?: string[]; subject: { any: boolean; note: string } };
export type Handover = { from: string; to: string; why: string };

export const WORKFLOWS = map.workflows as Workflow[];
export const STEPS = map.steps as Step[];
export const SHARED = map.shared as Shared[];
export const HANDOVERS = map.handovers as Handover[];

// Each step's live number: what that step has actually produced, read from the database now. A step the
// map says is not built has none — nothing is invented for it.
export type Measure = { n: number; words: string; when: string | null };

export async function measures(): Promise<Record<string, Measure>> {
  const [r] = await sql<
    {
      sets: number; approved: number; items: number; item_sets: number; old_papers: number; old_children: number;
      prescriptions: number; prescribed_at: string | null; worksheets: number; printed: number; approved_packs: number;
      captures: number; captured_at: string | null; answers: number; waiting: number; checked: number;
      evidence: number; graphs: number; corrections: number;
    }[]
  >`
    select
      (select count(*) from skill_set)::int as sets,
      (select count(*) from skill_set where status = 'ratified')::int as approved,
      (select count(*) from item where status = 'active')::int as items,
      (select count(distinct skill_set_code) from item where status = 'active')::int as item_sets,
      (select count(*) from capture c join sheet_instance si on si.id = c.sheet_instance_id
         join sheet_template t on t.id = si.sheet_template_id where c.superseded_by is null and t.source = 'legacy')::int as old_papers,
      (select count(distinct si.child_id) from capture c join sheet_instance si on si.id = c.sheet_instance_id
         join sheet_template t on t.id = si.sheet_template_id where c.superseded_by is null and t.source = 'legacy')::int as old_children,
      (select count(*) from prescription)::int as prescriptions,
      (select max(created_at)::text from prescription) as prescribed_at,
      (select count(*) from sheet_template where source = 'library' and retired_at is null)::int as worksheets,
      (select count(*) from sheet_instance where qr_code like 'CS%')::int as printed,
      (select count(*) from sheet_instance where qr_code like 'CS%' and print_status <> 'new')::int as approved_packs,
      (select count(*) from capture where superseded_by is null)::int as captures,
      (select max(created_at)::text from capture) as captured_at,
      (select count(*) from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null)::int as answers,
      (select count(*) from item_result r join capture c on c.id = r.capture_id
         where c.superseded_by is null and r.state = 'candidate' and r.status in ('unreadable', 'needs_teacher'))::int as waiting,
      (select count(*) from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null and r.state = 'confirmed')::int as checked,
      (select count(*) from read_correction)::int as corrections,
      (select count(*) from evidence_event where confirmed_by is not null)::int as evidence,
      (select count(distinct child_id) from child_skill_state)::int as graphs`;
  return {
    N1: { n: r.sets, words: `skill sets, ${r.approved} approved`, when: null },
    N2: { n: r.items, words: `questions ready, across ${r.item_sets} skill sets`, when: null },
    N3: { n: r.old_papers, words: `old papers read in, for ${r.old_children} children`, when: null },
    N5: { n: r.prescriptions, words: "papers chosen for a child", when: r.prescribed_at },
    N6: { n: r.worksheets, words: `numbered worksheets; ${r.printed} papers printed for a child`, when: null },
    N7: { n: r.approved_packs, words: `of ${r.printed} printed papers approved`, when: null },
    N8: { n: r.captures, words: "scans in", when: r.captured_at },
    N9: { n: r.answers, words: `answers read; ${r.waiting} wait for a person; ${r.corrections} readings a person gave`, when: null },
    N10: { n: r.evidence, words: `pieces of evidence; ${r.graphs} children with a graph`, when: null },
  };
}

// Where a step's output goes: every later step that takes something this step gives.
export function handsOnTo(step: Step): Step[] {
  return STEPS.filter((s) => s.code !== step.code && s.takes.some((t) => step.gives.includes(t)));
}
