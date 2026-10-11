"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icons, type IconName } from "./icons";

export type NavItem = { href: string; label: string; icon: IconName; match: readonly string[]; count?: number };

export function Nav({ items }: { items: readonly NavItem[] }) {
  const path = usePathname();
  // The item whose match is the longest prefix of the page: /worksheets/CS… is a child's paper, an assessment, though
  // /worksheets is the curriculum's library.
  const hits = (it: NavItem) =>
    Math.max(-1, ...it.match.map((m) => (m === "/" ? (path === "/" ? 1 : -1) : path.startsWith(m) ? m.length : -1)));
  const current = items.reduce<NavItem | undefined>((best, it) => (hits(it) > (best ? hits(best) : -1) ? it : best), undefined);
  return (
    <nav className="flex flex-row flex-wrap gap-[3px] md:flex-col" aria-label="Sections">
      {items.map((it) => {
        const Icon = Icons[it.icon];
        const active = it === current;
        return (
          <Link
            key={it.href}
            href={it.href}
            aria-current={active ? "page" : undefined}
            aria-describedby={it.count ? `waiting-${it.label}` : undefined}
            className={`flex min-h-11 items-center gap-[11px] px-[11px] py-[10px] text-[14px] no-underline ${
              active ? "bg-terracotta/28 text-chalk" : "text-bamboo hover:text-chalk"
            }`}
          >
            <span className={active ? "opacity-100" : "opacity-85"}>
              <Icon />
            </span>
            {it.label}
            {/* the count is the link's description, not its name: the tab is "Assessments" to a reader and a test */}
            {it.count ? (
              <span data-testid="waiting" aria-hidden="true" className="ml-auto min-w-[22px] bg-terracotta px-[6px] py-[1px] text-center text-[11.5px] text-chalk tabular-nums">
                {it.count.toLocaleString("en-IN")}
              </span>
            ) : null}
          </Link>
        );
      })}
      {items.map((it) =>
        it.count ? (
          <span key={`waiting-${it.label}`} id={`waiting-${it.label}`} className="sr-only">
            {it.count.toLocaleString("en-IN")} waiting
          </span>
        ) : null,
      )}
    </nav>
  );
}
