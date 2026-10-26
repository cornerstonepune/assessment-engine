// Check answers by assessment (goals/asm2_by_topic_and_checking.yaml). Nimish, 26 Oct 2026: "When I come to needs checking,
// everyone checks the assessment by the last upload that they do." The queue (`checkQueue`) already runs one assessment at a
// time; this says what each assessment is, from the few papers in the queue only, and never reads the page's answers again.
import { sql } from "./db";
import type { QueueEntry } from "./queries-read";

export type PaperFacts = {
  paper_id: string;
  kind: string;
  section: string | null;
  band: string | null;
  day: string | null;
  level: string | null;
  title: string;
  topics: string[];
  skills: string[];
};

/** What each paper in the queue is a copy of, by paper. */
export async function paperFacts(
  paperIds: string[],
): Promise<Map<string, PaperFacts>> {
  if (!paperIds.length) return new Map();
  const rows = await sql<PaperFacts[]>`
    select si.id as paper_id, coalesce(si.kind, 'earlier') as kind, coalesce(si.section, ch.section) as section,
           class_band(si.tenant_id, coalesce(si.section, ch.section)) as band, coalesce(t.key ->> 'date', si.created_at::date::text) as day,
           t.difficulty as level, coalesce(t.key ->> 'title', t.code, t.batch_id, si.qr_code) as title,
           coalesce(tk.topics, '{}'::text[]) as topics, coalesce(tk.skill_names, '{}'::text[]) as skills
    from sheet_instance si
    join sheet_template t on t.id = si.sheet_template_id
    join child ch on ch.id = si.child_id
    cross join lateral (
      select array_agg(distinct s.topic_code) filter (where s.topic_code is not null) as topics, array_agg(distinct s.name) as skill_names
      from skill s
      where s.tenant_id = t.tenant_id
        and (s.code = t.skill_set_code or s.code in (select i.skill_set_code from item i where i.id = any(t.item_ids)))
    ) tk
    where si.id = any(${paperIds}::uuid[])`;
  return new Map(rows.map((r) => [r.paper_id, r]));
}

export type CheckPaper = {
  paper_id: string;
  code: string;
  roll: string;
  answers: number;
  spots: number;
  first: string;
};
export type CheckGroup = {
  key: string;
  facts: PaperFacts;
  levels: string[];
  papers: CheckPaper[];
  answers: number;
  spots: number;
  /** The day the oldest answer waiting came in. */
  oldest: string;
  /** The first answer of the assessment, where checking it starts. */
  first: string;
};

/** The queue's entries (already in the order they are checked) as assessments, each with its papers. */
export function groupQueue(
  entries: QueueEntry[],
  facts: Map<string, PaperFacts>,
): CheckGroup[] {
  const out = new Map<string, CheckGroup>();
  for (const e of entries) {
    const f = facts.get(e.paper_id);
    if (!f) continue;
    const g = out.get(e.assessment) ?? {
      key: e.assessment,
      facts: f,
      levels: [],
      papers: [],
      answers: 0,
      spots: 0,
      oldest: e.captured,
      first: e.id,
    };
    if (f.level && !g.levels.includes(f.level)) g.levels.push(f.level);
    let p = g.papers.find((x) => x.paper_id === e.paper_id);
    if (!p)
      g.papers.push(
        (p = {
          paper_id: e.paper_id,
          code: e.code,
          roll: e.roll_no,
          answers: 0,
          spots: 0,
          first: e.id,
        }),
      );
    if (e.spot) {
      p.spots++;
      g.spots++;
    } else {
      p.answers++;
      g.answers++;
    }
    if (e.captured < g.oldest) g.oldest = e.captured;
    out.set(e.assessment, g);
  }
  return [...out.values()];
}

/** The first names of the children of some papers, read through pii.read_child, which logs who asked (rule 6): asked for the
 *  one assessment that is open, never for the whole queue. */
export async function firstNames(
  paperIds: string[],
  actor: string,
): Promise<Map<string, string>> {
  if (!paperIds.length) return new Map();
  const rows = await sql<{ id: string; first_name: string }[]>`
    select si.id, n.first_name from sheet_instance si, lateral pii.read_child(si.child_id, ${actor}) n where si.id = any(${paperIds}::uuid[])`;
  return new Map(rows.map((r) => [r.id, r.first_name]));
}
