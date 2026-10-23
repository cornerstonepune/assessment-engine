// Marking read three ways (goals/u3-marking.yaml): by class, by child, by worksheet — each row where its answers
// stand — and, opened, one child's papers or one worksheet's papers. Nimish, 2026-09-22: a student's name, then their
// papers, then every question of one paper, so each child's ladder is whole once their papers are signed off.
import Link from "@/components/link";
import { notFound } from "next/navigation";
import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import { Body, PageHeader, Panel } from "@/components/shell";
import type { Column } from "@/lib/ux-rules";
import type { PaperRow } from "@/lib/queries-read";
import { PapersTable, groupState, nextStep, standing, standingColumns, type Standing } from "./parts";

// as the database orders a roll (`roll_order`): by its first number, a roll with none last
const roll = (r: string) => Number(r.match(/\d{1,9}/)?.[0] ?? Number.MAX_SAFE_INTEGER);
const groupBy = <T,>(rows: T[], key: (r: T) => string) =>
  rows.reduce<Map<string, T[]>>((m, r) => m.set(key(r), [...(m.get(key(r)) ?? []), r]), new Map());

type Group = { key: string; name: string; href: string; children: number; rows: PaperRow[]; s: Standing };
const group = (key: string, name: string, href: string, rows: PaperRow[]): Group => ({ key, name, href, children: new Set(rows.map((r) => r.child_id)).size, rows, s: standing(rows) });

// By class and by worksheet: one table each, a row a class or a worksheet, where its answers stand in columns that add up
// to the sentence above the page (goals/u3-marking.yaml, goals/uxn8-marking.yaml).
function Groups({ groups, first, label, page, pageHref }: { groups: Group[]; first: string; label: string; page: number; pageHref: (n: number) => string }) {
  const columns: Column<Group>[] = [
    { key: "name", label: first, value: (g) => g.name, cell: (g) => <Link href={g.href}>{g.name}</Link> },
    { key: "children", label: "Children", num: true, width: "6rem", value: (g) => g.children },
    ...standingColumns<Group>((g) => g.s),
  ];
  return <DataTable label={label} columns={columns} rows={groups} rowKey={(g) => g.key} more={{ page, href: pageHref }} />;
}

export function ByClass({ papers, page, pageHref }: { papers: PaperRow[]; page: number; pageHref: (n: number) => string }) {
  const classes = [...groupBy(papers, (p) => p.section).entries()].sort(([a], [b]) => a.localeCompare(b));
  return (
    <Panel title="By class" aside={`${classes.length} class${classes.length === 1 ? "" : "es"}`}>
      <Groups
        groups={classes.map(([section, rows]) => group(section, section, `/capture?by=child&class=${encodeURIComponent(section)}`, rows))}
        first="Class"
        label="By class"
        page={page}
        pageHref={pageHref}
      />
    </Panel>
  );
}

const STEP_STATE = (rows: PaperRow[]): { state: State; words?: string } => {
  const s = standing(rows);
  return rows.every((p) => p.n_results === 0) ? { state: "unreadable", words: "nothing read" } : { state: groupState(s), words: s.waiting || s.toSign ? undefined : "signed off" };
};

type Kid = { rows: PaperRow[]; first: PaperRow };

/** By child (goals/ux5b-make-and-marking.yaml, goals/uxn8-marking.yaml): a table of each class's children — Roll, Child,
 *  Paper, Waiting, Status, Next step. With no class chosen each class is its own table of its first ten, and a link to the
 *  rest; with one chosen, its children are paged. */
export function ByChild({ papers, section, page, pageHref }: { papers: PaperRow[]; section?: string; page: number; pageHref: (n: number) => string }) {
  const kids: Kid[] = [...groupBy(papers, (p) => p.child_id).values()]
    .map((rows) => ({ rows, first: rows[0] }))
    .sort((a, b) => a.first.section.localeCompare(b.first.section) || roll(a.first.roll_no) - roll(b.first.roll_no) || a.first.first_name.localeCompare(b.first.first_name));
  const columns: Column<Kid>[] = [
    { key: "roll", label: "Roll", num: true, width: "4.5rem", value: (k) => k.first.roll_no },
    { key: "child", label: "Child", width: "9rem", value: (k) => k.first.first_name, cell: (k) => <Link href={`/capture?child=${k.first.child_id}`}>{k.first.first_name}</Link> },
    {
      key: "paper",
      label: "Paper",
      // several papers are opened from the child's name, which lists them
      value: (k) => (k.rows.length === 1 ? (k.first.title ?? k.first.paper) : `${k.rows.length} papers`),
      cell: (k) => (k.rows.length === 1 ? <Link href={`/capture/${k.first.id}`}>{k.first.title ?? k.first.paper}</Link> : `${k.rows.length} papers`),
    },
    { key: "waiting", label: "Waiting", num: true, width: "6rem", value: (k) => standing(k.rows).waiting },
    { key: "state", label: "Status", status: true, width: "11rem", value: (k) => STEP_STATE(k.rows).state, cell: (k) => <StatusChip {...STEP_STATE(k.rows)} /> },
    {
      key: "next",
      label: "Next step",
      width: "11rem",
      keep: true,
      value: (k) => nextStep(k.rows)?.words,
      cell: (k) => {
        const step = nextStep(k.rows);
        return step ? <Link href={step.href}>{step.words}</Link> : null;
      },
    },
  ];
  if (!kids.length) return <p className="note">No papers read yet.</p>;
  return (
    <section aria-label="By child">
      {section ? (
        <DataTable label={`Each child · ${section}`} columns={columns} rows={kids} rowKey={(k) => k.first.child_id} more={{ page, href: pageHref }} />
      ) : (
        <DataTable label="Each child" columns={columns} rows={kids} rowKey={(k) => k.first.child_id} more={{ by: (k) => k.first.section, href: (s: string) => `/capture?by=child&class=${encodeURIComponent(s)}` }} />
      )}
    </section>
  );
}

export function ByWorksheet({ papers, page, pageHref }: { papers: PaperRow[]; page: number; pageHref: (n: number) => string }) {
  const sheets = [...groupBy(papers, (p) => p.worksheet).entries()].sort(
    ([, a], [, b]) => (b[0].date ?? "").localeCompare(a[0].date ?? "") || (a[0].title ?? "").localeCompare(b[0].title ?? ""),
  );
  return (
    <Panel title="By worksheet" aside={`${sheets.length} worksheet${sheets.length === 1 ? "" : "s"}`}>
      <Groups
        groups={sheets.map(([key, rows]) => group(key, rows[0].title ?? key, `/capture?worksheet=${encodeURIComponent(key)}`, rows))}
        first="Worksheet"
        label="By worksheet"
        page={page}
        pageHref={pageHref}
      />
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
          <Link href="/capture?by=worksheet" className="text-[13px]">
            ← Every worksheet
          </Link>
        </p>
        <Panel title="Each child's copy" aside={`${s.signed} of ${s.papers} signed off`}>
          <PapersTable label="Each child's copy" rows={[...rows].sort((a, b) => a.section.localeCompare(b.section) || roll(a.roll_no) - roll(b.roll_no))} withChild />
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
          <Link href={`/capture?by=child&class=${encodeURIComponent(c.section)}`} className="text-[13px]">
            ← {c.section}
          </Link>
          <Link href={`/growth/${c.child_id}`} className="text-[13px]">
            {c.first_name}&rsquo;s page
          </Link>
          {next ? (
            <Link href={`/capture?child=${next.child_id}`} className="ml-auto text-[13px]">
              Next child to check: {next.first_name} →
            </Link>
          ) : null}
        </p>
        <Panel title="Papers" aside={s.toSign === 0 ? "all signed off" : `${s.toSign} to sign off`}>
          <PapersTable label="Papers" rows={read} />
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
    <Panel id="nothing-came-back" title="Read, but nothing came back" aside={<StatusChip state="unreadable" words={`${broken.length} papers`} />}>
      <p className="note mb-3">
        These papers were opened and produced no answers at all. A paper entered with the wrong questions, or a read
        that failed part way — either way nothing here counts for anything yet.
      </p>
      <PapersTable label="Read, but nothing came back" rows={broken} withChild />
    </Panel>
  );
}
