import { cache } from "react";
import { notFound } from "next/navigation";
import type { Session } from "./auth";
import { sql } from "./db";
import { engineSend } from "./engine";
import { PART_KEYS, PART_WORDS, type PagePart, type PartKey } from "./page-part";

// The curriculum screens (task M1-13): the browser, the fill view and its walk-through, the offered-skills queue. Reads
// are rows the site reads for itself; every answer is the engine's (POST /curriculum/page/* and /curriculum/offers/*),
// made as the signed-in member of staff. All of it behind the educator gate (D-076): the educator switch, or the staff preview.

/** The eight parts of a page, in the order a person reads them, with the school's words. */
export const SLOTS = [...PART_KEYS, "skills"] as const;
export type Slot = (typeof SLOTS)[number];
export const SLOT_WORDS: Record<Slot, string> = { ...PART_WORDS, skills: "Skills" };
export const PAGE_SIZE = 10;

export type State = "green" | "amber" | "red";
/** green when the share filled reaches `green`, amber from `amber`, else red — both bars are config rows. */
export const stateOf = cache(async (): Promise<(share: number) => State> => {
  const [green, amber] = await Promise.all([bar("curriculum.fill_green"), bar("curriculum.fill_amber")]);
  return (share) => (share >= green ? "green" : share >= amber ? "amber" : "red");
});

/** Whether the curriculum screens are open to this sign-in, once per request: the engine's gate (the educator switch on,
 *  the staff preview, or a role the review names). Not open, or not on the staff list, is not found. `reviews`: they may
 *  keep, edit, send back and answer offers; without it the staff preview looks and changes nothing (D-076). */
export const mustBeOn = cache(async (email: string): Promise<{ reviews: boolean }> => {
  const res = await engineSend("/curriculum/page/gate", { actor: email });
  if (res.status === 403 || res.status === 404) notFound();
  if (!res.ok) throw new Error(`The engine refused that (${res.status}).`);
  return (await res.json()) as { reviews: boolean };
});

/** The grade these screens list: the config row `curriculum.screens_grade` (the code of a row of `grade`). */
const grade = cache(async () => {
  const [row] = await sql<{ v: string | null }[]>`select (select value #>> '{}' from config where key = 'curriculum.screens_grade') as v`;
  if (!row?.v) throw new Error("config curriculum.screens_grade is missing: run engine load");
  return row.v;
});

/** A number from the config table; a missing row is a seed not loaded (`engine load`), said so rather than guessed. */
const bar = cache(async (key: string) => {
  const [row] = await sql<{ v: string | null }[]>`select (select value #>> '{}' from config where key = ${key}) as v`;
  const n = Number(row?.v);
  if (row?.v == null || !Number.isFinite(n)) throw new Error(`config ${key} is missing: run engine load`);
  return n;
});

export type SectionFill = { section: string; total: number; filled: Record<Slot, number>; share: number; state: State };

export async function sections(): Promise<SectionFill[]> {
  const band = await grade();
  const [rows, state] = await Promise.all([
    sql<(Record<Slot, number> & { section: string; total: number })[]>`
      select a.strand as section, count(*)::int as total,
        count(*) filter (where btrim(a.objective) <> '')::int as objective,
        count(*) filter (where btrim(a.materials) <> '')::int as materials,
        count(*) filter (where btrim(a.steps) <> '')::int as steps,
        count(*) filter (where btrim(a.thinking) <> '')::int as thinking,
        count(*) filter (where btrim(a.level_0) <> '')::int as level_0,
        count(*) filter (where btrim(a.level_1) <> '')::int as level_1,
        count(*) filter (where btrim(a.level_2) <> '')::int as level_2,
        count(*) filter (where btrim(a.level_3) <> '')::int as level_3,
        count(*) filter (where exists (select 1 from activity_skill k where k.tenant_id = a.tenant_id and k.activity_code = a.code))::int as skills
      from activity a where a.band = ${band} group by a.strand order by a.strand`,
    stateOf(),
  ]);
  return rows.map(({ section, total, ...filled }) => {
    const share = total ? SLOTS.reduce((n, s) => n + filled[s], 0) / (total * SLOTS.length) : 0;
    return { section, total, filled, share, state: state(share) };
  });
}

export type Row = { code: string; name: string; section: string; filled: number; state: State };

/** One page of activities, optionally of one section and matching a search of the name or number. */
export async function activities(section: string, q: string, page: number): Promise<{ rows: Row[]; total: number }> {
  const [state, band] = await Promise.all([stateOf(), grade()]);
  const like = `%${q.replace(/[\\%_]/g, "\\$&")}%`;
  const where = sql`a.band = ${band} ${section ? sql`and a.strand = ${section}` : sql``} ${q ? sql`and (a.name ilike ${like} or a.code ilike ${like})` : sql``}`;
  const [[{ n }], rows] = await Promise.all([
    sql<{ n: number }[]>`select count(*)::int as n from activity a where ${where}`,
    sql<{ code: string; name: string; section: string; filled: number }[]>`
      select a.code, a.name, a.strand as section,
        ((btrim(a.objective) <> '')::int + (btrim(a.materials) <> '')::int + (btrim(a.steps) <> '')::int + (btrim(a.thinking) <> '')::int
         + (btrim(a.level_0) <> '')::int + (btrim(a.level_1) <> '')::int + (btrim(a.level_2) <> '')::int + (btrim(a.level_3) <> '')::int
         + exists (select 1 from activity_skill k where k.tenant_id = a.tenant_id and k.activity_code = a.code)::int) as filled
      from activity a where ${where} order by a.strand, a.code limit ${PAGE_SIZE} offset ${(page - 1) * PAGE_SIZE}`,
  ]);
  return { total: n, rows: rows.map((r) => ({ ...r, state: state(r.filled / SLOTS.length) })) };
}

export type Gap = { part: PartKey; school: number; drafted: number; person: number; empty: number };

/** Each part: whose words fill it. A part with words and no mark is the school's (as the engine reads a page). */
export const gap = cache(async (): Promise<Gap[]> => {
  const band = await grade();
  const rows = await sql<Gap[]>`
    with t as (
      select a.tenant_id, a.code, p.part, btrim(p.txt) as txt
      from activity a cross join lateral (values ('objective', a.objective), ('materials', a.materials), ('steps', a.steps), ('thinking', a.thinking), ('level_0', a.level_0), ('level_1', a.level_1), ('level_2', a.level_2), ('level_3', a.level_3)) as p(part, txt) where a.band = ${band})
    select t.part,
      count(*) filter (where t.txt <> '' and coalesce(s.source, 'school') = 'school')::int as school,
      count(*) filter (where t.txt <> '' and s.source = 'drafted')::int as drafted,
      count(*) filter (where t.txt <> '' and s.source = 'person')::int as person,
      count(*) filter (where t.txt = '')::int as empty
    from t left join activity_part_source s on s.tenant_id = t.tenant_id and s.activity_code = t.code and s.part = t.part
    group by t.part`;
  return PART_KEYS.map((p) => rows.find((r) => r.part === p) ?? { part: p, school: 0, drafted: 0, person: 0, empty: 0 });
});

export type Waiting = { code: string; part: PartKey };

/** The drafted parts waiting for a person (the materials are items, which the page read does not carry: not here), those a checker doubted first, then by activity number and part. */
export const waiting = cache(async (part?: string): Promise<Waiting[]> => {
  const band = await grade();
  return sql<Waiting[]>`
    select s.activity_code as code, s.part
    from activity_part_source s join activity a on a.tenant_id = s.tenant_id and a.code = s.activity_code
    where a.band = ${band} and s.source = 'drafted' and s.part <> 'materials' and btrim(case s.part when 'objective' then a.objective when 'steps' then a.steps when 'thinking' then a.thinking when 'level_0' then a.level_0 when 'level_1' then a.level_1 when 'level_2' then a.level_2 when 'level_3' then a.level_3 else '' end) <> ''
      ${part ? sql`and s.part = ${part}` : sql``}
    order by s.check_me desc, s.activity_code, array_position(${sql.array([...PART_KEYS])}::text[], s.part)`;
});

// ---- the page as the engine reads it (docs/notes/m1-12b-apply-and-edit.md) ----
export type ActivityPage = { code: string; name: string; section: string; parts: PagePart[] };

export async function readPage(me: Pick<Session, "email">, code: string): Promise<ActivityPage | null> {
  const res = await engineSend("/curriculum/page/read", { actor: me.email, code });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`The engine refused that (${res.status}).`);
  return (await res.json()) as ActivityPage;
}

// ---- the offered skills (docs/notes/m1-12c-skill-offers.md) ----
type Named = { code: string; name: string };
export type Offer = {
  id: string; kind: "offer" | "skill"; activity: { code: string; name: string; section: string };
  skills: Named[]; also: Named[]; confidence: number; reason: string;
};

export const readOffers = cache(async (email: string): Promise<Offer[]> => {
  const res = await engineSend("/curriculum/offers/list", { actor: email });
  if (!res.ok) throw new Error(`The engine refused that (${res.status}).`);
  return ((await res.json()) as { offers: Offer[] }).offers;
});

/** The skills each activity already carries (the school's, and any a person said yes to). */
export async function linked(codes: string[]): Promise<Map<string, Named[]>> {
  if (!codes.length) return new Map();
  const rows = await sql<{ activity_code: string; code: string; name: string }[]>`
    select k.activity_code, k.skill_code as code, coalesce(s.name, '') as name
    from activity_skill k left join registry_skill s on s.tenant_id = k.tenant_id and s.code = k.skill_code
    where k.activity_code = any(${codes}) order by k.activity_code, k.skill_code`;
  const out = new Map<string, Named[]>();
  for (const r of rows) out.set(r.activity_code, [...(out.get(r.activity_code) ?? []), { code: r.code, name: r.name }]);
  return out;
}

/** How many slips a thinking part may hold: the config row `k2.format` (`slips_max`). */
export const slipsMax = cache(async (): Promise<number> => {
  const [row] = await sql<{ v: string | null }[]>`select (select value ->> 'slips_max' from config where key = 'k2.format') as v`;
  const n = Number(row?.v);
  if (!Number.isInteger(n) || n < 1) throw new Error("config k2.format has no slips_max: run engine load");
  return n;
});
