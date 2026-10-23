import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { kindWords } from "@/components/question";
import { StatusChip } from "@/components/status-chip";
import type { ReaderReport } from "@/lib/queries-read";
import type { Column } from "@/lib/ux-rules";
import { dateWords } from "@/lib/week";

// How the reader is doing, as one table (goals/u10-tables-read-straight.yaml, goals/uxn8-marking.yaml). Nimish, 2026-09-30:
// "is there just one view that we can have? It simply shows just one table, which can have a toggle around confidence
// levels, the date, etc. … which very clearly shows how the engine is improving or not". By day comes first: each day's
// share right, and how far it moved from the day before. The toggle is the filter row's own "Show".

const share = (a: number, b: number) => (b ? Math.round((100 * a) / b) : null);
const pct = (n: number | null) => (n === null ? "—" : `${n}%`);

export const READER_VIEWS = [
  ["kind", "By kind of question"],
  ["sure", "By how sure it was"],
] as const;
export type ReaderView = "day" | (typeof READER_VIEWS)[number][0];

export function ReaderTable({ r, words, view, page, keep }: { r: ReaderReport; words: Record<string, string>; view: ReaderView; page: number; keep: Record<string, string | undefined> }) {
  // days come newest first; each day's move is against the day read before it
  const days = r.days.map((d, i) => {
    const now = share(d.right, d.stood_behind);
    const before = r.days[i + 1] ? share(r.days[i + 1].right, r.days[i + 1].stood_behind) : null;
    return { ...d, now, moved: now === null || before === null ? null : now - before };
  });
  const href = (n: number) => `/capture?${new URLSearchParams({ ...Object.fromEntries(Object.entries(keep).filter(([, v]) => v) as [string, string][]), reader: view, rpage: String(n) })}`;
  const label = "How the reader is doing";
  type Day = (typeof days)[number];
  const dayCols: Column<Day>[] = [
    { key: "day", label: "Papers read on", width: "10rem", value: (d) => dateWords(d.day), cell: (d) => <span className="fact whitespace-nowrap">{dateWords(d.day)}</span> },
    { key: "checked", label: "Answers checked", num: true, value: (d) => d.checked },
    { key: "right", label: "Reader right", num: true, value: (d) => pct(d.now) },
    {
      key: "moved",
      label: "Against the day before",
      status: true,
      width: "12rem",
      value: (d) => (d.moved === null ? null : d.moved === 0 ? "no change" : d.moved),
      cell: (d) =>
        d.moved === null ? null : d.moved === 0 ? (
          "no change"
        ) : (
          <StatusChip state={d.moved > 0 ? "up" : "down"} words={`${d.moved > 0 ? "▲" : "▼"} ${Math.abs(d.moved)} points`} />
        ),
    },
    { key: "gave", label: "Gave up", num: true, value: (d) => d.gave_up },
  ];
  type Kind = ReaderReport["kinds"][number];
  const kindCols: Column<Kind>[] = [
    { key: "kind", label: "Kind of question", value: (k) => kindWords(words, k.fmt) },
    { key: "checked", label: "Answers checked", num: true, value: (k) => k.checked },
    { key: "right", label: "Reader right", num: true, value: (k) => pct(share(k.right, k.checked - k.gave_up)) },
    { key: "gave", label: "Gave up", num: true, value: (k) => k.gave_up },
    { key: "window", label: `Last ${r.window}`, num: true, value: (k) => `${k.window_right} of ${k.window_n}` },
    {
      key: "standing",
      label: "Standing",
      status: true,
      width: "15rem",
      value: (k) => (k.trusted ? "trusted" : "a person checks"),
      cell: (k) => (k.trusted ? <StatusChip state="trusted" words="trusted: settles alone" /> : <StatusChip state="waiting" words="a person checks every answer" />),
    },
    { key: "to", label: "Checks to trust", num: true, value: (k) => (k.to_trust === 0 ? "trusted" : `${k.to_trust} more`) },
  ];
  type Band = ReaderReport["bands"][number];
  const bandCols: Column<Band>[] = [
    { key: "sure", label: "Reader was this sure", value: (b) => `${b.lo}–${Math.min(b.hi, 100)}%`, cell: (b) => <span className="fact">{b.lo}–{Math.min(b.hi, 100)}%</span> },
    { key: "n", label: "Answers checked", num: true, value: (b) => b.n },
    { key: "right", label: "Right", num: true, value: (b) => pct(share(b.right, b.n)) },
    {
      key: "today",
      label: "Today",
      status: true,
      width: "12rem",
      value: (b) => (b.lo >= r.floor ? "stands alone" : "a person checks"),
      cell: (b) => (b.lo >= r.floor ? <StatusChip state="done" words="stands alone" /> : <StatusChip state="waiting" words="a person checks" />),
    },
  ];
  return (
    <div className="mt-4">
      <FilterBar action="/capture" keep={keep} filters={[{ name: "reader", label: "Show", value: view === "day" ? undefined : view, all: "By day", options: READER_VIEWS }]} />
      {view === "sure" ? (
        <p className="note mb-2">
          An answer stands on its own only when the reader is at least {Math.round(r.floor)}% sure; below that a person checks it. When the
          bands just under that line are right nearly every time, the line can come down and fewer answers wait.
        </p>
      ) : null}
      {view === "day" ? (
        <DataTable label={label} columns={dayCols} rows={days} rowKey={(d) => d.day} more={{ page, href }} />
      ) : view === "kind" ? (
        <DataTable label={label} columns={kindCols} rows={r.kinds} rowKey={(k) => k.fmt} more={{ page, href }} />
      ) : (
        <DataTable label={label} columns={bandCols} rows={r.bands} rowKey={(b) => String(b.lo)} more={{ page, href }} />
      )}
    </div>
  );
}
