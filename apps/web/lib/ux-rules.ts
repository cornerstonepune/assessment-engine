// The rules every page of the educator's site is held to (docs/ux-rules.md, goals/uxf-ux-foundation.yaml). One place for
// the numbers, so the blocks and the tests that fail the build read the same ones.

/** Rule 3: no long tables. A table shows at most this many rows; more are grouped or paged. */
export const TABLE_ROW_LIMIT = 10;
/** Rule 4: the line under a page's title says what the page is for, in one breath. */
export const PURPOSE_MAX = 140;

/** The top bar (docs/ux-rules.md, "Desktop first"): Class and Subject are full-size controls, the student search a compact field. */
export const TOP_BAR_MIN_PX = 40;
export const TOP_BAR_TEXT_PX = 15;
export const SEARCH_PX = 240;
/** A table of more rows than this has a filter row above it (rule 9). */
export const FILTER_FROM_ROWS = 6;

/** A cell that says nothing: nothing, a dash, or a zero. A column made only of these is not shown (rule 4). */
export function isEmptyCell(v: unknown): boolean {
  if (v == null || v === false) return true;
  const s = String(v).trim();
  return s === "" || /^[-–—]$/.test(s) || /^0+([.,]0+)?$/.test(s);
}

export type Column<T> = {
  key: string;
  label: string;
  /** What the cell holds, as a value: emptiness is read from this, not from what is drawn. */
  value: (row: T) => string | number | null | undefined;
  /** How it is drawn, when more than the value (a link, a chip). */
  cell?: (row: T) => React.ReactNode;
  /** A number: right-aligned, heading and cells. */
  num?: boolean;
  /** A state (a StatusChip): centred, heading and cells. Everything else is text, on the left. */
  status?: boolean;
  /** A fixed width, in a CSS length ("9rem"): every table of a kind draws a column the same width. */
  width?: string;
  /** Shown even when every row is empty: a column the educator acts in. */
  keep?: boolean;
};

export function visibleColumns<T>(columns: readonly Column<T>[], rows: readonly T[]): Column<T>[] {
  return columns.filter((c) => c.keep || rows.length === 0 || rows.some((r) => !isEmptyCell(c.value(r))));
}

/** The rows of page `page` (from 1) of `limit`, and how many pages there are. */
export function pageOf<T>(rows: readonly T[], page: number, limit = TABLE_ROW_LIMIT) {
  const pages = Math.max(1, Math.ceil(rows.length / limit));
  const at = Math.min(Math.max(1, Math.floor(page) || 1), pages);
  return { rows: rows.slice((at - 1) * limit, at * limit), page: at, pages };
}

/** Rows in the order given, kept in groups in order of first appearance: the caller sorts what needs the educator first. */
export function groupRows<T>(rows: readonly T[], group: (r: T) => string): { name: string; rows: T[] }[] {
  const out = new Map<string, T[]>();
  for (const r of rows) out.set(group(r), [...(out.get(group(r)) ?? []), r]);
  return [...out].map(([name, rs]) => ({ name, rows: rs }));
}

/** The alignment of a column, one rule for the whole site: text left, numbers right, a state centred. */
export const alignOf = (c: Pick<Column<unknown>, "num" | "status">): "left" | "right" | "center" => (c.num ? "right" : c.status ? "center" : "left");
