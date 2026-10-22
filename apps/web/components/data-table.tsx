import Link from "@/components/link";
import { type Column, TABLE_ROW_LIMIT, groupRows, pageOf, visibleColumns } from "@/lib/ux-rules";

// How the rows past the limit are reached, required so a table that can outgrow the limit cannot be written without a way
// to see the rest: grouped (a week, a class — one table each, the group's own rows capped, `href` to its rest) or paged.
export type More<T> =
  | { by: (row: T) => string; href?: (group: string) => string }
  | { page: number; href: (page: number) => string };

// The one table of the site (rule 2): the same head, the same number alignment, the same empty-column hiding (rule 4), at
// most `limit` rows (rule 3) and, on a phone, a list: each row a card, each cell labelled (rule 7, globals.css `table.list`).
// The caller sends the rows with what needs the educator first; this shows the first rows of each group or page.
export function DataTable<T>({
  label,
  columns,
  rows,
  rowKey,
  more,
  limit = TABLE_ROW_LIMIT,
}: {
  label: string;
  columns: readonly Column<T>[];
  rows: readonly T[];
  rowKey: (row: T) => string;
  more: More<T>;
  limit?: number;
}) {
  const cols = visibleColumns(columns, rows);
  if ("by" in more) {
    const { by, href } = more;
    return (
      <div className="grid gap-4">
        {groupRows(rows, by).map((g) => (
          <section key={g.name} aria-label={g.name}>
            <h3 className="mb-1 text-[14px]">{g.name}</h3>
            <Grid label={`${label} · ${g.name}`} cols={cols} rows={g.rows.slice(0, limit)} rowKey={rowKey} />
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
      <Grid label={label} cols={cols} rows={p.rows} rowKey={rowKey} />
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

function Grid<T>({ label, cols, rows, rowKey }: { label: string; cols: Column<T>[]; rows: readonly T[]; rowKey: (r: T) => string }) {
  return (
    <table className="grid list" aria-label={label}>
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c.key} scope="col" className={c.num ? "num" : undefined}>{c.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={rowKey(r)}>
            {cols.map((c) => (
              <td key={c.key} data-label={c.label} className={c.num ? "num" : undefined}>
                {c.cell ? c.cell(r) : (c.value(r) ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
