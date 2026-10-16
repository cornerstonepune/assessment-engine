// Marking read three ways (goals/u3-marking.yaml): by class, by child, by worksheet — each row where its answers
// stand — and, opened, one child's papers or one worksheet's papers. Nimish, 2026-09-22: a student's name, then their
// papers, then every question of one paper, so each child's ladder is whole once their papers are signed off.
import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import type { PaperRow } from "@/lib/queries-read";
import { many } from "@/lib/needs-you";
import { PaperTable, STANDING_HEADS, StandingCells, TotalRow, nextStep, standing } from "./parts";

// as the database orders a roll (`roll_order`): by its first number, a roll with none last
const roll = (r: string) => Number(r.match(/\d{1,9}/)?.[0] ?? Number.MAX_SAFE_INTEGER);
const groupBy = <T,>(rows: T[], key: (r: T) => string) =>
  rows.reduce<Map<string, T[]>>((m, r) => m.set(key(r), [...(m.get(key(r)) ?? []), r]), new Map());

export function ByClass({ papers }: { papers: PaperRow[] }) {
  const classes = [...groupBy(papers, (p) => p.section).entries()].sort(([a], [b]) => a.localeCompare(b));
  return (
    <Panel title="By class" aside={`${classes.length} class${classes.length === 1 ? "" : "es"}`}>
      <div className="min-w-0 overflow-x-auto">
        <table className="grid">
          <thead>
            <tr>
              <th>Class</th>
              <th className="num">Children</th>
              {STANDING_HEADS}
            </tr>
          </thead>
          <tbody>
            {classes.map(([section, rows]) => (
              <tr key={section}>
                <td>
                  <Link href={`/capture?by=child&class=${encodeURIComponent(section)}`}>{section}</Link>
                </td>
                <td className="num">{new Set(rows.map((r) => r.child_id)).size}</td>
                <StandingCells s={standing(rows)} />
              </tr>
            ))}
          </tbody>
          <TotalRow rows={papers} span={2} kids={new Set(papers.map((r) => r.child_id)).size} />
        </table>
      </div>
    </Panel>
  );
}

/** By child (goals/ux5b-make-and-marking.yaml): each class one line saying what waits in it, open to its children —
 *  Roll, Child, Paper, Waiting, Next step. `open` says which classes start open: the educator's own, or the one asked
 *  for; the coordinator's every class is one closed line. */
export function ByChild({ papers, open }: { papers: PaperRow[]; open: (section: string) => boolean }) {
  const classes = [...groupBy(papers, (p) => p.section).entries()].sort(([a], [b]) => a.localeCompare(b));
  return (
    <section aria-label="By child" className="panel min-w-0">
      {classes.length ? (
        classes.map(([section, rows]) => <ClassLine key={section} section={section} rows={rows} open={open(section)} />)
      ) : (
        <p className="note p-[18px]">No papers read yet.</p>
      )}
    </section>
  );
}

function ClassLine({ section, rows, open }: { section: string; rows: PaperRow[]; open: boolean }) {
  const children = [...groupBy(rows, (p) => p.child_id).values()].sort(
    (a, b) => roll(a[0].roll_no) - roll(b[0].roll_no) || a[0].first_name.localeCompare(b[0].first_name),
  );
  const s = standing(rows);
  // only what waits is said: a class with nothing waiting is one short line
  const waits = [s.waiting ? `${many(s.waiting, "answer")} to check` : "", s.toSign ? `${many(s.toSign, "paper")} to sign off` : ""].filter(Boolean);
  if (!waits.length) waits.push("nothing waiting");
  return (
    <details data-class={section} open={open} className="group border-t border-basalt/10 px-[18px] first:border-t-0">
      <summary className="flex cursor-pointer list-none items-baseline gap-x-2 py-3 text-[13.5px] [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className="inline-block w-3 text-basalt/50 transition-transform group-open:rotate-90">
          ▸
        </span>
        <span className="font-semibold text-basalt">{section}</span>
        <span className="text-basalt/70">· {[many(children.length, "child", "children"), ...waits].join(" · ")}</span>
      </summary>
      <div className="min-w-0 overflow-x-auto pb-3">
        <table className="grid" aria-label={`${section}: each child`}>
          <thead>
            <tr>
              <th>Roll</th>
              <th>Child</th>
              {/* on a phone the paper folds away: the child's name opens their papers, and the next step stays on screen */}
              <th className="max-sm:hidden">Paper</th>
              <th className="num">Waiting</th>
              <th>Next step</th>
            </tr>
          </thead>
          <tbody>
            {children.map((c) => {
              const [first] = c;
              const step = nextStep(c);
              const waiting = standing(c).waiting;
              return (
                <tr key={first.child_id}>
                  <td className="fact">{first.roll_no}</td>
                  <td>
                    <Link href={`/capture?child=${first.child_id}`}>{first.first_name}</Link>
                  </td>
                  <td className="max-w-[280px] text-[13px] max-sm:hidden">
                    {/* several papers are opened from the child's name, which lists them */}
                    {c.length === 1 ? <Link href={`/capture/${first.id}`}>{first.title ?? first.paper}</Link> : `${c.length} papers`}
                  </td>
                  <td className="num">{waiting ? <Pill tone="bamboo">{waiting}</Pill> : "—"}</td>
                  <td className="whitespace-nowrap">{step ? <Link href={step.href}>{step.words}</Link> : <Pill tone="neem">Signed off</Pill>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function ByWorksheet({ papers }: { papers: PaperRow[] }) {
  const sheets = [...groupBy(papers, (p) => p.worksheet).entries()].sort(
    ([, a], [, b]) => (b[0].date ?? "").localeCompare(a[0].date ?? "") || (a[0].title ?? "").localeCompare(b[0].title ?? ""),
  );
  return (
    <Panel title="By worksheet" aside={`${sheets.length} worksheet${sheets.length === 1 ? "" : "s"}`}>
      <div className="min-w-0 overflow-x-auto">
        <table className="grid">
          <thead>
            <tr>
              <th>Worksheet</th>
              <th className="num">Children</th>
              {STANDING_HEADS}
            </tr>
          </thead>
          <tbody>
            {sheets.map(([key, rows]) => (
              <tr key={key}>
                <td className="max-w-[300px] text-[13px]">
                  <Link href={`/capture?worksheet=${encodeURIComponent(key)}`}>{rows[0].title ?? key}</Link>
                </td>
                <td className="num">{new Set(rows.map((r) => r.child_id)).size}</td>
                <StandingCells s={standing(rows)} />
              </tr>
            ))}
          </tbody>
          <TotalRow rows={papers} span={2} kids={new Set(papers.map((r) => r.child_id)).size} />
        </table>
      </div>
    </Panel>
  );
}

/** One worksheet: every child's copy of it. */
export function WorksheetPapers({ papers, worksheet }: { papers: PaperRow[]; worksheet: string }) {
  const rows = papers.filter((p) => p.worksheet === worksheet);
  if (!rows.length) notFound();
  const s = standing(rows);
  return (
    <>
      <PageHeader
        stage="Assessments · marking by worksheet"
        title={rows[0].title ?? worksheet}
        sub={`${s.papers} children's copies read: ${s.engine} answers settled by the engine, ${s.person} checked by a person, ${s.waiting} still waiting.`}
      />
      <Body>
        <p className="mb-4">
          <Link href="/capture?by=worksheet" className="chip">
            ← Every worksheet
          </Link>
        </p>
        <Panel title="Each child's copy" aside={`${s.signed} of ${s.papers} signed off`}>
          <PaperTable rows={[...rows].sort((a, b) => a.section.localeCompare(b.section) || roll(a.roll_no) - roll(b.roll_no))} withChild />
        </Panel>
      </Body>
    </>
  );
}

/** One child's papers, oldest first — the order the paper page steps through with "Next paper". */
export function ChildPapers({ papers, id }: { papers: PaperRow[]; id: string }) {
  const all = papers.filter((p) => p.child_id === id);
  if (!all.length) notFound();
  const c = all[0];
  const read = all.filter((p) => p.n_results > 0).sort((a, b) => (a.date ?? "9999").localeCompare(b.date ?? "9999"));
  const s = standing(all);
  // the next child in roll order who still has a paper to sign off
  const children = [...groupBy(papers, (p) => p.child_id).values()].sort(
    (a, b) => a[0].section.localeCompare(b[0].section) || roll(a[0].roll_no) - roll(b[0].roll_no),
  );
  const at = children.findIndex((k) => k[0].child_id === id);
  const next = children.slice(at + 1).find((k) => standing(k).toSign > 0)?.[0];
  return (
    <>
      <PageHeader
        stage={`Assessments · marking · ${c.section}`}
        title={c.first_name}
        sub={`Roll ${c.roll_no}. ${read.length} paper${read.length === 1 ? "" : "s"} read, ${s.toSign} still to sign off. Open a paper, check every answer against ${c.first_name}'s writing, then sign it off.`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href={`/capture?by=child&class=${encodeURIComponent(c.section)}`} className="chip">
            ← {c.section}
          </Link>
          <Link href={`/growth/${c.child_id}`} className="chip">
            {c.first_name}&rsquo;s page
          </Link>
          {next ? (
            <Link href={`/capture?child=${next.child_id}`} className="chip ml-auto">
              Next child to check: {next.first_name} →
            </Link>
          ) : null}
        </p>
        <Panel title="Papers" aside={s.toSign === 0 ? "all signed off" : `${s.toSign} to sign off`}>
          <PaperTable rows={read} />
        </Panel>
      </Body>
    </>
  );
}

/** Papers opened that produced no answers: nothing on them counts yet, and someone should look. */
export function NothingRead({ papers }: { papers: PaperRow[] }) {
  const broken = papers.filter((p) => p.n_results === 0);
  if (!broken.length) return null;
  return (
    <Panel id="nothing-came-back" title="Read, but nothing came back" aside={<Pill tone="terracotta">{broken.length}</Pill>}>
      <p className="note mb-3">
        These papers were opened and produced no answers at all. A paper entered with the wrong questions, or a read
        that failed part way — either way nothing here counts for anything yet.
      </p>
      <PaperTable rows={broken} withChild />
    </Panel>
  );
}
