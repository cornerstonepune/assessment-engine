import Link from "@/components/link";
import { type Column, TABLE_ROW_LIMIT, alignOf, groupRows, pageOf, visibleColumns } from "@/lib/ux-rules";

// How the rows past the limit are reached, required so a table that can outgrow the limit cannot be written without a way
// to see the rest: grouped (a week, a class — one table each, the group's own rows capped, `href` to its rest) or paged.
export type More<T> =
  | { by: (row: T) => string; href?: (group: string) => string }
  | { page: number; href: (page: number) => string };

// What a row can carry beyond its cells: data attributes (for a test or a link target), and a row of its own under it,
// full width (an assessment opened to its copies).
// A table that sorts: the column it is sorted by, which way a screen reader says that is ("other" where the order is what
// needs doing first), and the address of the table sorted by another column. The caller does the sorting; every sortable
// heading is a link to it.
export type Sort = { key: string; dir: "ascending" | "descending" | "other"; href: (key: string) => string };

export type RowExtras<T> = { attrs?: (row: T) => Record<string, string>; expand?: (row: T) => React.ReactNode };

// The one table of the site (rule 2): fixed column widths, text on the left, numbers on the right, a state in the middle,
// a head that stays at the top while the rows scroll, a row that lights under the pointer; the same head, the same number alignment, the same empty-column hiding (rule 4), at
// most `limit` rows (rule 3) and, on a phone, a list: each row a card, each cell labelled (rule 7, globals.css `table.list`).
// The caller sends the rows with what needs the educator first; this shows the first rows of each group or page.
export function DataTable<T>({
  label,
  columns,
  rows,
  rowKey,
  more,
  limit = TABLE_ROW_LIMIT,
  extras,
  sort,
  dense,
}: {
  label: string;
  columns: readonly Column<T>[];
  rows: readonly T[];
  rowKey: (row: T) => string;
  more: More<T>;
  limit?: number;
  extras?: RowExtras<T>;
  sort?: Sort;
  /** Less room beside each cell, for a table of many narrow columns (the steps of an assessment). */
  dense?: boolean;
}) {
  const cols = visibleColumns(columns, rows);
  if ("by" in more) {
    const { by, href } = more;
    return (
      <div className="grid gap-4">
        {groupRows(rows, by).map((g) => (
          <section key={g.name} aria-label={g.name}>
            <h3 className="mb-1 text-[14px]">{g.name}</h3>
            <Grid label={`${label} · ${g.name}`} cols={cols} rows={g.rows.slice(0, limit)} rowKey={rowKey} extras={extras} sort={sort} dense={dense} />
            {g.rows.length > limit ? (
              <p className="note mt-1">
                {g.rows.length - limit} more in {g.name}
                {href ? (
                  <>
                    {" · "}
                    <Link href={href(g.name)}>Show all →</Link>
                  </>
                ) : null}
              </p>
            ) : null}
          </section>
        ))}
      </div>
    );
  }
  const p = pageOf(rows, more.page, limit);
  return (
    <div>
      <Grid label={label} cols={cols} rows={p.rows} rowKey={rowKey} extras={extras} sort={sort} dense={dense} />
      {p.pages > 1 ? (
        <nav className="mt-2 flex items-center gap-3 text-[13px]" aria-label={`${label} pages`}>
          {p.page > 1 ? <Link href={more.href(p.page - 1)} className="chip">← Earlier</Link> : null}
          <span>Page {p.page} of {p.pages}</span>
          {p.page < p.pages ? <Link href={more.href(p.page + 1)} className="chip">Later →</Link> : null}
        </nav>
      ) : null}
    </div>
  );
}

function Grid<T>({ label, cols, rows, rowKey, extras, sort, dense }: { label: string; cols: Column<T>[]; rows: readonly T[]; rowKey: (r: T) => string; extras?: RowExtras<T>; sort?: Sort; dense?: boolean }) {
  const cls = (c: Column<T>) => `a-${alignOf(c)}`;
  return (
    <div className="data-table">
      <table className={`grid list steady${dense ? " dense" : ""}`} aria-label={label}>
        <colgroup>
          {cols.map((c) => (
            <col key={c.key} style={c.width ? { width: c.width } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c.key} scope="col" className={`${cls(c)}${c.num ? " num" : ""}`} aria-sort={sort && c.sortable && c.key === sort.key ? sort.dir : undefined}>
                {sort && c.sortable ? (
                  <Link href={sort.href(c.key)} className={`no-underline ${c.key === sort.key ? "text-basalt" : "text-inherit"}`}>
                    {c.label}
                    {c.key === sort.key ? " ▾" : ""}
                  </Link>
                ) : (
                  c.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.flatMap((r) => {
            const under = extras?.expand?.(r);
            return [
              <tr key={rowKey(r)} {...(extras?.attrs?.(r) ?? {})}>
                {cols.map((c) => (
                  <td key={c.key} data-label={c.label} className={`${cls(c)}${c.num ? " num" : ""}`}>
                    {c.cell ? c.cell(r) : <Value v={c.value(r)} />}
                  </td>
                ))}
              </tr>,
              under ? (
                <tr key={`${rowKey(r)}|under`} className="under">
                  <td colSpan={cols.length}>{under}</td>
                </tr>
              ) : null,
            ];
          })}
        </tbody>
      </table>
    </div>
  );
}

// A cell with nothing in it says so, quietly, so a row never has a hole in it; a column of nothing is not drawn at all.
function Value({ v }: { v: string | number | null | undefined }) {
  return v == null || v === "" ? <span className="text-basalt/45">—</span> : <>{v}</>;
}
