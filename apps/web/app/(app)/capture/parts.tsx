// The pieces every Marking view shares (goals/u3-marking.yaml): where a group of papers' answers stand, a table of
// papers, and how the reader is doing. The counts are the engine's (answer_standing); nothing here decides one.
import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { Panel } from "@/components/shell";
import { StatusChip, type State } from "@/components/status-chip";
import type { Column } from "@/lib/ux-rules";
import { many } from "@/lib/needs-you";
import { questionKinds } from "@/lib/question-types";
import type { PaperRow, ReaderReport } from "@/lib/queries-read";
import { ReaderTable, type ReaderView } from "./reader-table";
import { dateWords } from "@/lib/week";

export const fmtDate = dateWords;

/** A group of papers — a class, a child, a worksheet, everything — and where the answers on them stand. */
export type Standing = {
  papers: number;
  answers: number;
  engine: number;
  person: number;
  waiting: number;
  signed: number;
  toSign: number;
  answersToSign: number;
};

export function standing(rows: PaperRow[]): Standing {
  const read = rows.filter((p) => p.n_results > 0);
  return {
    papers: read.length,
    answers: rows.reduce((n, p) => n + p.n_results, 0),
    engine: rows.reduce((n, p) => n + p.n_engine, 0),
    person: rows.reduce((n, p) => n + p.n_person, 0),
    waiting: rows.reduce((n, p) => n + p.n_waiting, 0),
    signed: read.filter((p) => p.n_candidate === 0).length,
    toSign: read.filter((p) => p.n_candidate > 0).length,
    answersToSign: read.reduce((n, p) => n + p.n_candidate, 0),
  };
}

/** The standing of a group of papers as table columns, labelled for a test to read (`data-testid`). Every answer read is
 *  settled by the engine, checked by a person or still waiting, so the three after "Answers read" add up to it. A column
 *  of zeros is not drawn (docs/ux-rules.md, rule 4). */
export function standingColumns<T>(of: (row: T) => Standing): Column<T>[] {
  const n = (key: string, label: string, pick: (s: Standing) => number, width = "6rem"): Column<T> => ({
    key,
    label,
    num: true,
    width,
    value: (r) => pick(of(r)),
    cell: (r) => <span data-testid={key}>{pick(of(r))}</span>,
  });
  return [
    n("papers", "Papers in", (s) => s.papers, "5.5rem"),
    n("answers", "Answers read", (s) => s.answers),
    n("engine", "Settled by the engine", (s) => s.engine, "7rem"),
    n("person", "Checked by a person", (s) => s.person, "7rem"),
    n("waiting", "Still waiting", (s) => s.waiting),
    {
      key: "signed",
      label: "Signed off",
      width: "8rem",
      value: (r) => of(r).papers,
      cell: (r) => (of(r).papers === 0 ? null : <span className="whitespace-nowrap">{of(r).signed === of(r).papers ? `all ${of(r).papers} signed off` : `${of(r).signed} of ${of(r).papers} signed off`}</span>),
    },
    {
      key: "state",
      label: "Status",
      status: true,
      width: "10rem",
      value: (r) => groupState(of(r)),
      cell: (r) => <StatusChip state={groupState(of(r))} />,
    },
  ];
}

/** Where a group of papers stands: answers waiting for a person first, then papers to sign off, then all signed off. */
export const groupState = (s: Standing): State => (s.waiting ? "toCheck" : s.toSign ? "toSignOff" : "done");

/** What a child's papers need next (goals/ux5b-make-and-marking.yaml): the answers waiting for a person, then a paper
 *  to sign off — on the one paper that holds them, or across their papers when several do; a paper that came back with
 *  nothing read is looked at; else nothing, every paper signed off. */
export function nextStep(rows: PaperRow[]): { words: string; href: string } | null {
  const at = (some: PaperRow[]) => (some.length === 1 ? `/capture/${some[0].id}` : `/capture?child=${some[0].child_id}`);
  const waiting = rows.filter((p) => p.n_waiting > 0);
  if (waiting.length) return { words: `Check ${many(standing(waiting).waiting, "answer")} →`, href: at(waiting) };
  const sign = rows.filter((p) => p.n_results > 0 && p.n_candidate > 0);
  if (sign.length) return { words: sign.length === 1 ? "Sign off →" : `Sign off ${sign.length} papers →`, href: at(sign) };
  if (rows.some((p) => p.n_results === 0)) return { words: "Nothing came back: look →", href: "#nothing-came-back" };
  return null;
}

/** Where one paper stands. */
const paperState = (p: PaperRow): { state: State; words?: string } =>
  p.n_results === 0
    ? { state: "unreadable", words: "nothing read" }
    : p.n_candidate === 0
      ? { state: "done", words: "signed off" }
      : p.n_flagged > 0
        ? { state: "toCheck", words: `${p.n_flagged} need your eyes` }
        : { state: "toSignOff" };

/** Papers as one table (goals/uxn8-marking.yaml): what each is, how its answers stand, and where it stands. */
export function PapersTable({ rows, withChild = false, label, page = 1, pageHref }: { rows: PaperRow[]; withChild?: boolean; label: string; page?: number; pageHref?: (n: number) => string }) {
  const columns: Column<PaperRow>[] = [
    ...(withChild
      ? [{ key: "child", label: "Child", width: "9rem", value: (p: PaperRow) => p.first_name, cell: (p: PaperRow) => (
          <>
            <Link href={`/capture?child=${p.child_id}`}>{p.first_name}</Link>
            <div className="text-[12px] text-basalt/55">{p.section}</div>
          </>
        ) }]
      : []),
    { key: "paper", label: "Paper", value: (p) => p.title ?? p.paper, cell: (p) => <Link href={`/capture/${p.id}`}>{p.title ?? p.paper}</Link> },
    { key: "sat", label: "Sat", num: true, width: "8rem", value: (p) => fmtDate(p.date), cell: (p) => <span className="fact whitespace-nowrap">{fmtDate(p.date)}</span> },
    { key: "answers", label: "Answers", num: true, width: "5.5rem", value: (p) => p.n_results },
    { key: "engine", label: "By the engine", num: true, width: "6rem", value: (p) => p.n_engine },
    { key: "person", label: "By a person", num: true, width: "6rem", value: (p) => p.n_person },
    { key: "waiting", label: "Waiting", num: true, width: "5.5rem", value: (p) => p.n_waiting },
    {
      key: "score",
      label: "Score",
      num: true,
      width: "7.5rem",
      // A score once nothing on the sheet waits for a person: right, of every answer that counts.
      value: (p) => (p.n_results > 0 && p.n_flagged === 0 ? `${p.n_right} / ${p.n_scored} right` : null),
      cell: (p) => (p.n_results > 0 && p.n_flagged === 0 ? <span className="whitespace-nowrap">{`${p.n_right} / ${p.n_scored} right`}</span> : null),
    },
    { key: "state", label: "Status", status: true, width: "11rem", value: (p) => paperState(p).state, cell: (p) => <StatusChip {...paperState(p)} /> },
  ];
  return <DataTable label={label} columns={columns} rows={rows} rowKey={(p) => p.id} more={{ page, href: pageHref ?? (() => "") }} />;
}

// Every check teaches the reader about that child (ADR 0032); this says what the checks so far add up to, so the effort
// can be seen to pay, and whether the reader is getting better: one table, by day first (`ReaderTable`).
// It is the reader's record, in every class: its trust in a kind of question is earned across the school (`kind_trust`),
// so it is never narrowed to a person's classes, and it says so beside their own counts (goals/ux8a-numbers-true.yaml).
const pct = (a: number, b: number) => (b ? `${Math.round((100 * a) / b)}%` : "—");

export async function ReaderPanel({ r, view, page, keep }: { r: ReaderReport; view: ReaderView; page: number; keep: Record<string, string | undefined> }) {
  const { words } = await questionKinds();
  const read = r.days.filter((d) => d.stood_behind > 0); // newest first
  const [latest, first] = [read[0], read[read.length - 1]];
  return (
    <Panel title="How the reader is doing" label="How the reader is doing" aside={`from ${r.checked} answers checked, in every class`}>
      <p className="text-[15px] leading-snug">
        In every class, people have checked {r.checked} answers the reader read. The reader was right on {r.right} of the {r.stood_behind} it stood behind ({pct(r.right, r.stood_behind)}),
        wrong on {r.stood_behind - r.right}, and gave up on {r.gave_up}{r.gave_up ? ` (its guess was right on ${r.guess_right})` : ""}.
        {first && latest && first !== latest
          ? ` On the first papers it read (${fmtDate(first.day)}) it was right on ${pct(first.right, first.stood_behind)}; on the latest (${fmtDate(latest.day)}), ${pct(latest.right, latest.stood_behind)}.`
          : ""}{" "}
        Every check you make teaches it how that child writes; a kind of question is settled by the reader alone only once it has matched you{" "}
        {Math.round(r.bar * 100)}% of the time over the last {r.window} checks. By kind of question says how many more right checks each still needs.
      </p>
      {r.days.length || r.kinds.length || r.bands.length ? <ReaderTable r={r} words={words} view={view} page={page} keep={keep} /> : null}
    </Panel>
  );
}
