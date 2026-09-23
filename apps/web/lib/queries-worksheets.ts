// The worksheet library (ADR 0026): every question in the bank on a numbered worksheet of twelve.
// A worksheet is a `sheet_template` row with source 'library'; which worksheets hold a question is
// read from their question ids, never copied onto the question.
import { sql } from "./db";
import { itemColumns, type ItemRow } from "./queries-bank";
import type { Difficulty } from "./queries";

export type WorksheetRow = {
  code: string;
  skill_set_code: string;
  skill: string;
  difficulty: Difficulty;
  kinds: Record<string, number>;
};

export type WorksheetFilter = { set?: string; level?: string };

const live = (f: WorksheetFilter) => sql`
  t.source = 'library' and t.retired_at is null
  ${f.set ? sql`and t.skill_set_code = ${f.set}` : sql``}
  ${f.level ? sql`and t.difficulty = ${f.level}` : sql``}`;

// In the order a teacher reads them: the ladder, then Easy to Advance, then the worksheet's number.
export async function worksheets(f: WorksheetFilter, limit: number, offset: number): Promise<WorksheetRow[]> {
  return sql<WorksheetRow[]>`
    select t.code, t.skill_set_code, s.name as skill, t.difficulty,
           (select json_object_agg(k.fmt, k.n) from (
              select i.fmt, count(*)::int as n from item i where i.id = any(t.item_ids) group by i.fmt) k) as kinds
    from sheet_template t
    join skill_set s on s.tenant_id = t.tenant_id and s.code = t.skill_set_code
    join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    where ${live(f)}
    order by r.ladder_order nulls last, s.code,
             array_position(array['Easy', 'Medium', 'Hard', 'Advance'], t.difficulty), t.variant
    limit ${limit} offset ${offset}`;
}

export async function worksheetCount(f: WorksheetFilter): Promise<number> {
  const [{ n }] = await sql<{ n: number }[]>`select count(*)::int as n from sheet_template t where ${live(f)}`;
  return n;
}

export type LibraryWorksheet = {
  code: string;
  skill_set_code: string;
  skill: string;
  outcome: string;
  band: string;
  difficulty: Difficulty;
  level_words: string | null;
  created_at: string;
  retired_at: string | null;
};

export async function libraryWorksheet(code: string): Promise<LibraryWorksheet | undefined> {
  const rows = await sql<LibraryWorksheet[]>`
    select t.code, t.skill_set_code, coalesce(s.name, t.skill_set_code) as skill,
           coalesce(s.learning_objective, '') as outcome, t.band, t.difficulty,
           s.difficulty -> t.difficulty ->> 'words' as level_words, t.created_at, t.retired_at
    -- a worksheet printed from a skill set since replaced (ADR 0034) still opens, under the name it was made for
    from sheet_template t left join skill_set s on s.tenant_id = t.tenant_id and s.code = t.skill_set_code
    where t.source = 'library' and t.code = ${code}`;
  return rows[0];
}

// A worksheet's questions in the order they print.
export async function worksheetItems(code: string): Promise<ItemRow[]> {
  return sql<ItemRow[]>`
    select ${itemColumns()} from sheet_template t, unnest(t.item_ids) with ordinality as u(id, n)
    join item i on i.id = u.id
    where t.source = 'library' and t.code = ${code}
    order by u.n`;
}
