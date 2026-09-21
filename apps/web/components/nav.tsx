"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icons, type IconName } from "./icons";

export type NavItem = { href: string; label: string; icon: IconName; match: readonly string[] };

export function Nav({ items }: { items: readonly NavItem[] }) {
  const path = usePathname();
  // The item whose match is the longest prefix of the page: /capture/check is "Check answers", not
  // "Capture & Mark" as well.
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
            className={`flex min-h-11 items-center gap-[11px] px-[11px] py-[10px] text-[14px] no-underline ${
              active ? "bg-terracotta/28 text-chalk" : "text-bamboo hover:text-chalk"
            }`}
          >
            <span className={active ? "opacity-100" : "opacity-85"}>
              <Icon />
            </span>
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
