import { sql } from "./db";

/** The one table a person approves beside the skills (step 8b): on these kinds of question, this named
 *  mistake counts against this skill instead of the one its operation would name. `waiting` is true
 *  until someone approves this exact table — a changed table waits again. */
export type ChargeRow = { kind: string; code: string; mistake: string; skill: string };
export type ChargesTable = { table: Record<string, Record<string, string>>; rows: ChargeRow[]; approvedBy: string | null; waiting: boolean };

export async function chargesTable(): Promise<ChargesTable> {
  const rows = await sql<{ key: string; value: unknown }[]>`
    select key, value from config where key in ('skills.charges_by_kind', 'skills.charges_by_kind.approved')`;
  const table = (rows.find((r) => r.key === "skills.charges_by_kind")?.value ?? {}) as Record<string, Record<string, string>>;
  const approved = (rows.find((r) => r.key === "skills.charges_by_kind.approved")?.value ?? {}) as {
    by?: string;
    table?: unknown;
  };
  const pairs = Object.entries(table).flatMap(([kind, m]) => Object.entries(m).map(([code, skill]) => ({ kind, code, skill })));
  const names = pairs.length
    ? await sql<{ code: string; mistake: string; skill: string; skill_name: string }[]>`
        select p.code, p.skill, mistake_name(p.code, p.skill) as mistake,
               (select k.name from skill k where k.code = p.skill limit 1) as skill_name
        from jsonb_to_recordset(${sql.json(pairs as never)}::jsonb) as p(kind text, code text, skill text)`
    : [];
  const named = new Map(names.map((n) => [`${n.code}|${n.skill}`, n]));
  return {
    table,
    rows: pairs.map((p) => ({
      kind: p.kind,
      code: p.code,
      mistake: named.get(`${p.code}|${p.skill}`)?.mistake ?? p.code,
      skill: named.get(`${p.code}|${p.skill}`)?.skill_name ?? p.skill,
    })),
    approvedBy: approved.by ?? null,
    waiting: !approved.by || JSON.stringify(approved.table) !== JSON.stringify(table),
  };
}
