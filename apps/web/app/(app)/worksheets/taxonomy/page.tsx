import Link from "@/components/link";
import { Body, PageHeader, Panel, Pill, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { type Held, type TaxonomyCase, standing, taxonomyMap, worksheetsOutsideTaxonomy } from "@/lib/queries-taxonomy";

// The worksheet library read by the school team's taxonomy (goals/s12-worksheets-by-taxonomy.yaml): each
// section, each case with the document's example, the level the rules set it at, and the worksheets holding it.

const CHAPTERS: Record<string, string> = {
  "2": "Addition",
  "3": "Subtraction",
  "4": "Lining up columns",
  "5": "Carry and exchange patterns",
  "6": "Missing numbers and digits",
  "7": "Equality and checking",
  "8": "Mental strategies",
  "9": "Estimation",
  "10": "Word problems",
  "11": "Finding the mistake",
};

const TONE = {
  "on its level": "neem",
  "across levels": "monsoon",
  "away from its level": "terracotta",
  "on no worksheet": "terracotta",
} as const;

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function WorksheetsByTaxonomy({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  const [all, outside] = await deadline(Promise.all([taxonomyMap(), worksheetsOutsideTaxonomy()]));
  const ch = q.ch && q.ch in CHAPTERS ? q.ch : "2";
  const tally = (s: string) => all.filter((c) => standing(c) === s).length;
  const shown = all.filter((c) => c.section.split(".")[0] === ch);
  const sections = [...new Set(shown.map((c) => c.section))];

  return (
    <>
      <PageHeader
        stage="Stage 2 · Print · by taxonomy"
        title="Worksheets by taxonomy"
        sub="The team's Addition & Subtraction taxonomy, case by case: the level the rules set each case at, and the worksheets that hold its questions."
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href="/worksheets#library" className="chip">
            ← Worksheets by skill and level
          </Link>
        </p>
        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-5">
          <Tile tone="neem" n={tally("on its level")} words="cases on worksheets at their own level" />
          <Tile tone="monsoon" n={tally("across levels")} words="patterns across many levels" />
          <Tile tone="terracotta" n={tally("away from its level")} words="only away from their level" />
          <Tile tone="terracotta" n={tally("on no worksheet")} words="on no worksheet" />
          <Tile tone="bamboo" n={outside} words="worksheets outside this taxonomy" />
        </div>
        <nav aria-label="Taxonomy chapters" className="mb-[18px] flex flex-wrap gap-2">
          {Object.entries(CHAPTERS).map(([k, words]) => (
            <Link
              key={k}
              href={`/worksheets/taxonomy?ch=${k}`}
              className={`chip ${k === ch ? "!bg-basalt !text-chalk" : ""}`}
              aria-current={k === ch ? "page" : undefined}
            >
              §{k} {words}
            </Link>
          ))}
        </nav>
        <div className="grid gap-[18px]">
          {sections.map((s) => {
            const rows = shown.filter((c) => c.section === s);
            return (
              <Panel key={s} title={`§${s} · ${rows[0].section_name}`} aside={`${rows.length} cases`}>
                <div className="overflow-x-auto">
                  <table className="grid" aria-label={`Cases in §${s}`}>
                    <thead>
                      <tr>
                        <th>Case</th>
                        <th>What it tests</th>
                        <th>Set at</th>
                        <th>On worksheets</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((c) => (
                        <CaseRow key={c.code} c={c} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            );
          })}
        </div>
        <p className="note mt-4">
          Which cases a question is, is measured from its numbers by the engine, never typed. “Across levels” is a
          pattern — the order of the numbers, how a carry falls — that questions at many levels show, so no one level
          owns it.
        </p>
      </Body>
    </>
  );
}

function CaseRow({ c }: { c: TaxonomyCase }) {
  const st = standing(c);
  return (
    <tr>
      <td className="align-top whitespace-nowrap">
        <span className="fact">{c.code}</span>
        <div className="mt-1">
          <Pill tone={TONE[st]}>{st}</Pill>
        </div>
      </td>
      <td className="min-w-[220px] align-top">
        {c.label}
        {c.example_text ? <div className="text-[12.5px] text-basalt/62">{c.example_text}</div> : null}
      </td>
      <td className="align-top text-[12.5px]">
        {c.set_at.length === 0 ? (
          <span className="text-basalt/62">no one level</span>
        ) : (
          c.set_at.map((p) => (
            <div key={`${p.set}-${p.level}`}>
              <Link href={`/skill-sets/${p.set}?level=${p.level}#worksheets`}>{p.name}</Link> · {p.level}
            </div>
          ))
        )}
      </td>
      <td className="min-w-[260px] align-top text-[12.5px]">
        {c.held.length === 0 ? <span className="text-terracotta">none yet</span> : null}
        {c.held.slice(0, 3).map((h) => (
          <HeldAt key={`${h.set}-${h.level}`} h={h} />
        ))}
        {c.held.length > 3 ? (
          <details className="mt-1">
            <summary className="cursor-pointer text-basalt/62">{c.held.length - 3} more levels</summary>
            {c.held.slice(3).map((h) => (
              <HeldAt key={`${h.set}-${h.level}`} h={h} />
            ))}
          </details>
        ) : null}
      </td>
    </tr>
  );
}

function HeldAt({ h }: { h: Held }) {
  return (
    <div className="mb-1">
      <Link href={`/worksheets?set=${h.set}&level=${h.level}#library`}>
        {h.name} · {h.level}
      </Link>{" "}
      <span className="text-basalt/62">
        — {h.questions} questions on {h.worksheets} worksheets:
      </span>{" "}
      {h.codes.map((code) => (
        <Link key={code} href={`/worksheets/${code}`} className="mr-1 inline-block font-mono whitespace-nowrap">
          {code}
        </Link>
      ))}
      {h.worksheets > h.codes.length ? <span className="text-basalt/62">…</span> : null}
    </div>
  );
}
