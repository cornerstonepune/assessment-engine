import Link from "@/components/link";
import { Icon } from "@/lib/icons";

// Where she is (D-075: a breadcrumb on every screen): Educator › This week › Mon 23 Nov. The last is the page itself.
export function Crumbs({ trail }: { trail: { label: string; href?: string }[] }) {
  return (
    <nav aria-label="Where you are" className="mb-[var(--space-3)]">
      <ol className="flex flex-wrap items-center gap-[var(--space-1)] text-[length:var(--text-label)] text-[var(--text-muted)]">
        {trail.map((t, i) => (
          <li key={t.label} className="inline-flex items-center gap-[var(--space-1)]">
            {i > 0 ? <Icon name="following" size={16} /> : null}
            {t.href ? (
              <Link href={t.href} className="inline-flex min-h-[var(--tap)] min-w-[var(--tap)] items-center text-[var(--link)]">
                {t.label}
              </Link>
            ) : (
              <span aria-current="page" className="font-medium text-[var(--text)]">
                {t.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
