import { sql } from "./db";
import { EVERY_CLASS } from "./scope";
import { paperList, type PaperFilter, type PaperListRow } from "./queries-papers";

// One assessment as one card (goals/s2-the-assessment-card.yaml), from the scope Nimish locked on 2026-10-22: "Every
// assessment is one card that moves through seven stages, and always shows its next step". An assessment is what the
// Assessments list groups (`assessmentList`): a kind of paper given to a class in a week on one skill set or worksheet,
// or a class's home assessments for a week. Where each copy stands is the list's own (`paperList`); this adds the
// educator's word that it was given and who was away (`flow_run`, written by the engine: w2_print/given.py), what a
// scan of it lacked (the read-scan runs), and how far a file being read has got.

export type CardKey = { class: string; week: string; kind: string; set?: string };

export type CardCopy = PaperListRow & { printed: boolean; printedOn: string | null; away: boolean; retake: string[] };

export type Card = {
  key: CardKey;
  copies: CardCopy[];
  spares: CardCopy[];
  given: { on: string; by: string } | null;
  /** A file being read now: its pages read of all, and the minutes left at the pace so far (null until a page is in). */
  reading: { pages: number; of: number; minutes: number | null } | null;
};

/** The stages, in order, in the school's words; the card is at the first not yet done. */
export const CARD_STAGES = ["Made", "Approved for print", "Given", "Papers in", "Read", "Checked", "Signed off", "Results"] as const;
export type CardStage = (typeof CARD_STAGES)[number];

const isIn = (c: PaperListRow) => !["made", "printed", "replaced"].includes(c.stage);

/** What the card counts: copies made, approved, in, away, still out, checked and signed off, and where it stands. */
export function standing(card: Card) {
  const copies = card.copies.filter((c) => c.stage !== "replaced");
  const n = copies.length;
  const approved = copies.filter((c) => c.printed).length;
  const inn = copies.filter(isIn);
  const away = copies.filter((c) => c.away && !isIn(c));
  const out = copies.filter((c) => !c.away && !isIn(c));
  const checked = inn.filter((c) => c.stage === "checked" || c.stage === "signed off").length;
  const signed = inn.filter((c) => c.stage === "signed off").length;
  const done: Record<CardStage, boolean> = {
    Made: n > 0,
    "Approved for print": n > 0 && approved === n,
    // an upload without "Given on" is still accepted: a paper in says it was given
    Given: !!card.given || inn.length > 0,
    "Papers in": n > 0 && out.length === 0 && inn.length > 0,
    Read: n > 0 && out.length === 0 && inn.length > 0 && !card.reading,
    Checked: inn.length > 0 && checked === inn.length,
    "Signed off": inn.length > 0 && signed === inn.length,
    Results: inn.length > 0 && signed === inn.length,
  };
  const at = CARD_STAGES.find((s) => !done[s]) ?? "Results";
  return { n, approved, inn: inn.length, away, out, checked, signed, waiting: inn.reduce((k, c) => k + c.waiting, 0), done, at };
}

/** The assessment's copies in roll order, its spares apart, with the educator's word and what the scans said. */
export async function assessmentCard(key: CardKey, actor: string): Promise<Card> {
  const f: PaperFilter = { class: key.class, week: key.week, kind: key.kind, set: key.set };
  const { rows } = await paperList(f, actor, EVERY_CLASS, "roll");
  const qrs = rows.map((r) => r.qr);
  const [printed, given, away, scans, [reading]] = await Promise.all([
    sql<{ qr: string; printed: boolean; on: string | null }[]>`
      select qr_code as qr, print_status <> 'new' as printed, to_char(coalesce(printed_at, approved_at), 'YYYY-MM-DD') as on
      from sheet_instance where qr_code = any(${qrs})`,
    sql<{ on: string; by: string }[]>`
      select request ->> 'on' as on, request ->> 'by' as by from flow_run
      where flow = 'given' and request -> 'qrs' ?| ${qrs}::text[] order by started_at desc, id desc limit 1`,
    // the newest word on each paper stands: away, or back
    sql<{ qr: string; away: boolean }[]>`
      select distinct on (request ->> 'qr') request ->> 'qr' as qr, (request ->> 'away')::boolean as away from flow_run
      where flow = 'absent' and request ->> 'qr' = any(${qrs}) order by request ->> 'qr', started_at desc, id desc`,
    // what the newest file holding each copy said it lacked: a page not in the file, a page twice, a copy not read
    sql<{ qr: string; lacks: string[]; why: string | null }[]>`
      select distinct on (c.value ->> 'code') c.value ->> 'code' as qr,
             array(select jsonb_array_elements_text(coalesce(c.value -> 'lacks', '[]'::jsonb))) as lacks,
             case when (c.value ->> 'skipped')::boolean then c.value ->> 'why' end as why
      from flow_run r cross join lateral jsonb_array_elements(coalesce(r.result -> 'copies', '[]'::jsonb)) c
      where r.flow = 'read-scan' and r.status = 'ok' and c.value ->> 'code' = any(${qrs})
      order by c.value ->> 'code', r.started_at desc`,
    // a file being read now, by any member of staff: its pages are sorted to their papers only as each is read
    sql<{ pages: number | null; of: number | null; secs: number | null }[]>`
      select (result -> 'read' ->> 'pages')::int as pages, coalesce((result -> 'read' ->> 'of')::int, (result ->> 'pages')::int) as of,
             extract(epoch from (result -> 'read' ->> 'at')::timestamptz - started_at)::int as secs
      from flow_run where flow = 'read-scan' and status = 'running' and started_at > now() - interval '2 hours'
      order by started_at desc limit 1`,
  ]);
  const p = new Map(printed.map((r) => [r.qr, r]));
  const off = new Set(away.filter((a) => a.away).map((a) => a.qr));
  const said = new Map(scans.map((s) => [s.qr, [...s.lacks, ...(s.why ? [`not read: ${s.why}`] : [])]]));
  const full = rows.map((r) => ({
    ...r,
    printed: !!p.get(r.qr)?.printed,
    printedOn: p.get(r.qr)?.on ?? null,
    away: off.has(r.qr),
    // what to photograph again: what the newest file holding the copy lacked; a copy read whole since says nothing
    retake: said.get(r.qr) ?? [],
  }));
  const minutes =
    reading?.pages && reading.of && reading.secs != null ? Math.max(1, Math.round(((reading.of - reading.pages) * reading.secs) / reading.pages / 60)) : null;
  return {
    key,
    copies: full.filter((c) => !c.spare && !c.extra),
    spares: full.filter((c) => c.spare),
    given: given[0] ?? null,
    reading: reading ? { pages: reading.pages ?? 0, of: reading.of ?? 0, minutes } : null,
  };
}
