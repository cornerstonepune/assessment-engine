"use client";

import { usePathname, useSearchParams } from "next/navigation";
import Link from "@/components/link";
import { Icon, type IconName } from "@/lib/icons";
import { E } from "@/lib/educator/words";

// Her timetable's menu (D-075): a left sidebar with submenus on a desktop, a bar of tabs at the foot of a phone. The
// class she picked and the day she is on go with every link.
type Item = {
  key: string;
  label: string;
  icon: IconName;
  path: string;
  sub?: { label: string; extra: string }[];
};
const ITEMS: Item[] = [
  {
    key: "today",
    label: E.nav.today,
    icon: "today",
    path: "/educator",
    sub: [{ label: E.nav.tomorrow, extra: "tomorrow" }],
  },
  {
    key: "week",
    label: E.nav.week,
    icon: "week",
    path: "/educator/week",
    sub: [{ label: E.nav.nextWeek, extra: "next" }],
  },
];

export function EducatorNav({ as }: { as: "side" | "tabs" }) {
  const path = usePathname();
  const q = useSearchParams();
  const keep = (extra?: string) => {
    const p = new URLSearchParams();
    const c = q.get("class");
    if (c) p.set("class", c);
    if (extra) p.set("go", extra);
    const s = p.toString();
    return s ? `?${s}` : "";
  };
  const on = (i: Item) =>
    i.path === "/educator"
      ? path === "/educator" || path.startsWith("/educator/period")
      : path.startsWith(i.path);
  if (as === "side")
    return (
      <nav aria-label={E.nav.label} data-educator-nav="side">
        <ul className="grid gap-[var(--space-1)]">
          {ITEMS.map((i) => (
            <li key={i.key}>
              <Link
                href={`${i.path}${keep()}`}
                aria-current={on(i) ? "page" : undefined}
                data-nav={i.key}
                className={`flex min-h-[var(--tap)] items-center gap-[var(--space-2)] rounded-[var(--radius-m)] px-[var(--space-2)] font-medium no-underline ${on(i) ? "bg-[var(--chip-donow-bg)] text-[var(--chip-donow-fg)]" : "text-[var(--text)] hover:bg-[var(--sunken)]"}`}
              >
                <Icon name={i.icon} />
                {i.label}
              </Link>
              {i.sub ? (
                <ul className="mt-[var(--space-1)] grid gap-[var(--space-1)] pl-[var(--space-5)]">
                  {i.sub.map((s) => (
                    <li key={s.extra}>
                      <Link
                        href={`${i.path}${keep(s.extra)}`}
                        data-nav={`${i.key}-${s.extra}`}
                        className="flex min-h-[var(--tap)] items-center text-[length:var(--text-label)] text-[var(--text-muted)] no-underline hover:text-[var(--text)]"
                      >
                        {s.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      </nav>
    );
  return (
    <nav
      aria-label={E.nav.label}
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--border)] bg-[var(--surface)] pb-[env(safe-area-inset-bottom)] md:hidden"
      data-educator-nav="tabs"
    >
      <ul className="grid grid-cols-2">
        {ITEMS.map((i) => (
          <li key={i.key}>
            <Link
              href={`${i.path}${keep()}`}
              aria-current={on(i) ? "page" : undefined}
              data-tab={i.key}
              className={`flex min-h-[var(--space-7)] flex-col items-center justify-center gap-[var(--space-1)] text-[length:var(--text-label)] font-medium no-underline ${on(i) ? "text-[var(--text)]" : "text-[var(--text-muted)]"}`}
            >
              <Icon name={i.icon} />
              {i.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
