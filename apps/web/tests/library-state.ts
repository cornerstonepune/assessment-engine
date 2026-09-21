// A test that removes or rewords a question also retires and makes worksheets (ADR 0026). These put
// one level's worksheets back exactly as the test found them — rows it made deleted, every earlier
// row's retirement as it was — so the next run starts from the same library.
import type postgres from "postgres";

type Snapshot = { id: string; retired_at: Date | null }[];

export async function libraryOf(sql: postgres.Sql, skillSet: string, level: string): Promise<Snapshot> {
  return sql<Snapshot>`
    select id, retired_at from sheet_template where source = 'library' and skill_set_code = ${skillSet} and difficulty = ${level}`;
}

export async function restoreLibrary(sql: postgres.Sql, skillSet: string, level: string, was: Snapshot): Promise<void> {
  await sql`delete from sheet_template where source = 'library' and skill_set_code = ${skillSet} and difficulty = ${level}
            and id <> all(${was.map((r) => r.id)}::uuid[])`;
  for (const r of was) await sql`update sheet_template set retired_at = ${r.retired_at} where id = ${r.id}`;
}
