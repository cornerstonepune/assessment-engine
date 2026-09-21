// The question bank and the papers drawn from it: what the bank holds, one question as every
// screen reads it, and a printed paper with the facts of how it was made.
import { sql } from "./db";
import type { Difficulty } from "./queries";

// A question's own numbers, by kind: `a op b` for most, `addends` for a long column, `base` for a
// number wall, `left`/`right` for a balance (null is the box the child fills), `planted` for the
// mistake a find-the-mistake question shows.
export type ItemSpec = {
  a?: number;
  b?: number;
  op?: string;
  addends?: number[];
  text?: string;
  question?: string;
  base?: number[];
  left?: (number | null)[];
  right?: (number | null)[];
  planted?: string;
};

// One thing the child writes. `answer` is null where a person reads it (an explanation) and
// `rubric` says how; `misconceptions` maps each named mistake to the wrong answer it produces.
export type ItemResponse = {
  rid: string;
  label?: string;
  answer: string | null;
  rubric?: string | null;
  tolerance?: number | null;
  misconceptions: Record<string, number>;
};

export type ItemRow = {
  id: string;
  item_key: string;
  fmt: string;
  stem: string;
  spec: ItemSpec;
  responses: ItemResponse[];
  status: string;
  times_used: number;
  skill_set_code: string | null;
  skill_set_name: string | null;
  difficulty: string | null;
};

export type ItemFilter = { set?: string; difficulty?: string; fmt?: string; status?: string };

// The columns every question is read with, the skill set's name included — a fragment, so the bank
// and a printed paper can never read a question two different ways.
const itemColumns = () => sql`
  i.id, i.item_key, i.fmt, i.stem, i.spec, i.responses, i.status, i.times_used, i.skill_set_code, i.difficulty,
  (select s.name from skill_set s where s.tenant_id = i.tenant_id and s.code = i.skill_set_code) as skill_set_name`;

// What the bank may print: generated questions, the live ones unless the removed ones are asked for.
const inBank = (f: ItemFilter) => sql`
  i.source = 'generated' and i.status = ${f.status === "retired" ? "retired" : "active"}
  ${f.set ? sql`and i.skill_set_code = ${f.set}` : sql``}
  ${f.difficulty ? sql`and i.difficulty = ${f.difficulty}` : sql``}
  ${f.fmt ? sql`and i.fmt = ${f.fmt}` : sql``}`;

export async function items(f: ItemFilter, limit: number, offset: number): Promise<ItemRow[]> {
  return sql<ItemRow[]>`
    select ${itemColumns()} from item i where ${inBank(f)}
    order by i.created_at desc, i.item_key
    limit ${limit} offset ${offset}`;
}

export async function itemCount(f: ItemFilter): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from item i where ${inBank(f)}`;
  return n;
}

export type BankRow = {
  code: string;
  name: string;
  band: string;
  fmts: string[];
  counts: Partial<Record<Difficulty, number>>;
};

// The whole bank at a glance: every skill set in ladder order, the kinds of question it holds, and
// how many are ready to print at each level — exactly the pools a paper is drawn from.
export async function bankGrid(): Promise<BankRow[]> {
  return sql<BankRow[]>`
    with b as (
      select skill_set_code, difficulty, fmt, count(*)::int as n from item
      where source = 'generated' and status = 'active' group by 1, 2, 3
    )
    select s.code, s.name, r.band,
           coalesce((select array_agg(distinct b.fmt order by b.fmt) from b where b.skill_set_code = s.code), '{}') as fmts,
           coalesce((select json_object_agg(d.difficulty, d.n)
                     from (select b.difficulty, sum(b.n)::int as n from b where b.skill_set_code = s.code
                           group by b.difficulty) d), '{}'::json) as counts
    from skill_set s
    join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    order by r.ladder_order nulls last, s.code`;
}

export async function bankTotals(): Promise<{ active: number; retired: number }> {
  const [t] = await sql<{ active: number; retired: number }[]>`
    select count(*) filter (where status = 'active')::int as active,
           count(*) filter (where status = 'retired')::int as retired
    from item where source = 'generated'`;
  return t;
}

export type PrintedPaper = {
  qr_code: string;
  print_status: string;
  approved_by: string | null;
  rendered: boolean;
  pages: number;
  week: string;
  difficulty: Difficulty;
  skill_set_name: string;
  n_items: number;
  roll_no: string | null;
  section: string | null;
  kind: string | null;
  rule_fired: string | null;
  override_reason: string | null;
  pool: number;
  window_days: number;
};

// One generated paper and the facts of how it was drawn: who it is for (roll number only — the
// name is printed on the page itself, never read into a row here), the pool it was drawn from, and
// the exposure window `assemble` honoured. A spare has no child and no prescription.
export async function printedPaper(qr: string): Promise<PrintedPaper | undefined> {
  const rows = await sql<PrintedPaper[]>`
    select si.qr_code, si.print_status, si.approved_by, si.pdf_path is not null as rendered,
           coalesce((st.key ->> 'pages')::int, 1) as pages, st.week, st.difficulty, s.name as skill_set_name,
           coalesce(array_length(st.item_ids, 1), 0) as n_items, c.roll_no, c.section,
           p.kind, p.rule_fired, p.override_reason,
           (select count(*)::int from item i where i.status = 'active' and i.source = 'generated'
              and i.skill_set_code = st.skill_set_code and i.difficulty = st.difficulty) as pool,
           (select t.value::int from threshold t where t.key = 'exposure.days') as window_days
    from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id
    join skill_set s on s.tenant_id = st.tenant_id and s.code = st.skill_set_code
    left join child c on c.id = st.child_id
    left join prescription p on p.sheet_instance_id = si.id
    where si.qr_code = ${qr} and st.source = 'generated'`;
  return rows[0];
}

// The paper's questions in the order they are printed.
export async function paperItems(qr: string): Promise<ItemRow[]> {
  return sql<ItemRow[]>`
    select ${itemColumns()}
    from sheet_instance si
    join sheet_template st on st.id = si.sheet_template_id
    cross join lateral unnest(st.item_ids) with ordinality as u(id, n)
    join item i on i.id = u.id
    where si.qr_code = ${qr}
    order by u.n`;
}

export type Mistake = { name: string; description: string | null };

// A mistake's name can depend on the operation it is made in — M_WRONG_OP is "added instead of
// subtracting" in a subtraction and "subtracted instead of adding" in an addition. Keyed `code@op`
// for every row, and plain `code` only where the name is the same whatever the operation, so a
// question that does not record its operation is never given another operation's name. Each comes
// with the sentence that shows what the mistake looks like on paper — which, on the plain key, is
// kept only where it too is the same for every operation ("one less than the correct difference:
// 62 − 27 written as 34" is no description of a mistake in an addition).
export async function mistakeBook(): Promise<Record<string, Mistake>> {
  const rows = await sql<{ key: string; name: string; description: string | null }[]>`
    select code || '@' || op as key, name, description from misconception
    union all
    select code, min(name), case when count(distinct description) = 1 then min(description) end
    from misconception group by code having count(distinct name) = 1`;
  return Object.fromEntries(rows.map((r) => [r.key, { name: r.name, description: r.description }]));
}

export type QuestionPage = ItemRow & {
  band: string;
  level_words: string | null;
  generator: string | null;
  skill_set_version: number | null;
  created_at: string;
  children: number;
  corrected_from_key: string | null;
  replaced_by_key: string | null;
  removed_by: string | null;
  removed_note: string | null;
};

// Everything about one question for its own page: the level's rule it was made to, where it came
// from, how many children have had it — and, for one that was removed or reworded, who did it, why,
// and which question took its place.
export async function questionPage(key: string): Promise<QuestionPage | undefined> {
  const rows = await sql<QuestionPage[]>`
    select ${itemColumns()}, r.band, s.difficulty -> i.difficulty ->> 'words' as level_words,
           i.generator, i.skill_set_version, i.created_at,
           (select count(distinct x.child_id)::int from item_exposure x where x.item_id = i.id) as children,
           (select o.item_key from item o where o.id = i.corrected_from) as corrected_from_key,
           (select n.item_key from item n where n.corrected_from = i.id order by n.created_at desc limit 1)
             as replaced_by_key,
           f.actor as removed_by, f.note as removed_note
    from item i
    join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code
    left join skill_set s on s.tenant_id = i.tenant_id and s.code = i.skill_set_code
    left join lateral (select actor, note from item_feedback
                       where item_id = i.id and verdict = 'retire' order by created_at desc limit 1) f on true
    where i.item_key = ${key} and i.source = 'generated'`;
  return rows[0];
}
