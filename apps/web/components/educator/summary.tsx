import Link from "@/components/link";

// The strip of counts at the top of a page (D-075): what the page holds, each count a link to the first of what it
// counts. A count of nothing is shown and not linked.
export function Summary({ items }: { items: { label: readonly [string, string]; n: number; href?: string }[] }) {
  return (
    <ul data-summary className="mb-[var(--space-3)] flex flex-wrap gap-[var(--space-2)]">
      {items.map((i) => (
        <li key={i.label[1]}>
          {i.href && i.n ? (
            <Link href={i.href} className="inline-flex min-h-[var(--tap)] items-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border)] px-[var(--space-3)] text-[var(--text)] no-underline hover:border-[var(--border-control)]">
              <span className="font-semibold tabular-nums">{i.n}</span> {i.label[i.n === 1 ? 0 : 1]}
            </Link>
          ) : (
            <span className="inline-flex min-h-[var(--tap)] items-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border)] px-[var(--space-3)] text-[var(--text-muted)]">
              <span className="font-semibold tabular-nums">{i.n}</span> {i.label[i.n === 1 ? 0 : 1]}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
