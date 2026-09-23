import { sql } from "./db";

// The worksheet library read by the school team's taxonomy (goals/s12-worksheets-by-taxonomy.yaml). Which
// cases a question is comes from `item.case_codes`, measured by the engine and held true by `engine audit`;
// nothing here decides it.

export type Place = { set: string; name: string; level: string };
export type Held = Place & { worksheets: number; questions: number; codes: string[] };
export type TaxonomyCase = {
  code: string;
  section: string;
  section_name: string;
  label: string;
  example_text: string;
  set_at: Place[]; // the levels whose rule names this case
  held: Held[]; // where its questions sit on live library worksheets, the most first
};

/** Every case, in the document's order, with the levels set for it and the worksheets holding it. */
export async function taxonomyMap(): Promise<TaxonomyCase[]> {
  return sql<TaxonomyCase[]>`
    with set_at as (
      select c.code, jsonb_agg(jsonb_build_object('set', s.code, 'name', s.name, 'level', d.key)
                               order by s.code, array_position(array['Easy','Medium','Hard','Advance'], d.key)) as places
      from skill_set s
      cross join lateral jsonb_each(s.difficulty) d
      cross join lateral jsonb_array_elements_text(coalesce(d.value -> 'check' -> 'cases', '[]'::jsonb)) c(code)
      group by c.code
    ),
    held as materialized (
      select x as code, t.skill_set_code as set, s.name, t.difficulty as level,
             count(distinct t.id)::int as worksheets, count(*)::int as questions,
             (array_agg(distinct t.code order by t.code))[1:8] as codes
      from sheet_template t
      join skill_set s on s.tenant_id = t.tenant_id and s.code = t.skill_set_code
      cross join lateral unnest(t.item_ids) u(id)
      join item i on i.id = u.id
      cross join lateral unnest(i.case_codes) x
      where t.source = 'library' and t.retired_at is null
      group by x, t.skill_set_code, s.name, t.difficulty
    )
    select tc.code, tc.section, tc.section_name, tc.label, tc.example_text,
           coalesce(sa.places, '[]'::jsonb) as set_at,
           coalesce((select jsonb_agg(jsonb_build_object('set', h.set, 'name', h.name, 'level', h.level,
                                                         'worksheets', h.worksheets, 'questions', h.questions,
                                                         'codes', h.codes) order by h.questions desc, h.set)
                     from held h where h.code = tc.code), '[]'::jsonb) as held
    from taxonomy_case tc
    left join set_at sa on sa.code = tc.code
    order by string_to_array(tc.section, '.')::int[], tc.code`;
}

/** Library worksheets that hold no taxonomy case — multiplication, explaining a claim — outside this document. */
export async function worksheetsOutsideTaxonomy(): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from sheet_template t
    where t.source = 'library' and t.retired_at is null
      and not exists (select 1 from unnest(t.item_ids) u(id) join item i on i.id = u.id where i.case_codes <> '{}')`;
  return n;
}

/** The cases one worksheet holds, and how many of its questions are each. */
export async function worksheetCases(code: string): Promise<{ code: string; label: string; section: string; n: number }[]> {
  return sql`
    select tc.code, tc.label, tc.section, count(*)::int as n
    from sheet_template t
    cross join lateral unnest(t.item_ids) u(id)
    join item i on i.id = u.id
    cross join lateral unnest(i.case_codes) x
    join taxonomy_case tc on tc.tenant_id = t.tenant_id and tc.code = x
    where t.code = ${code}
    group by tc.code, tc.label, tc.section
    order by string_to_array(tc.section, '.')::int[], tc.code`;
}

/** Where a case stands against the worksheets: on the level set for it, a pattern across levels, or not. */
export function standing(c: TaxonomyCase): "on its level" | "across levels" | "away from its level" | "on no worksheet" {
  if (c.held.length === 0) return "on no worksheet";
  if (c.set_at.length === 0) return "across levels";
  const at = new Set(c.set_at.map((p) => `${p.set}|${p.level}`));
  return c.held.some((h) => at.has(`${h.set}|${h.level}`)) ? "on its level" : "away from its level";
}
