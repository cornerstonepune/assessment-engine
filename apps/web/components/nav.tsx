"use client";

import NextLink from "next/link";
import Link from "./link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { GROUPS, locate, tabsOf, type MenuGroup } from "@/lib/menu";

// The menu on the top bar (goals/nav_teacher_scope_and_todo.yaml): the five groups, then under the bar the pages of the group
// you are in as tabs, and a three-line button that opens every group and its pages. Only the first group carries a count.
// Nothing here names a subject. Only the group links pre-load, as the old menu's did.

const bar = "relative flex min-h-11 items-center px-3 text-[14.5px] no-underline";

/** The five groups. `counts`: what waits, by group key. On a phone they fold into the menu button. */
export function GroupNav({ groups, counts }: { groups: readonly MenuGroup[]; counts: Partial<Record<string, number>> }) {
  const path = usePathname();
  const here = locate(path)?.group.key;
  return (
    <nav aria-label="Sections" className="flex min-w-0 items-stretch gap-1 max-md:hidden">
      {groups.map((g) => {
        const n = counts[g.key];
        return (
          <NextLink
            key={g.key}
            href={g.href}
            aria-current={g.key === here ? "page" : undefined}
            aria-describedby={n ? `waiting-${g.key}` : undefined}
            className={`${bar} gap-2 ${g.key === here ? "text-chalk shadow-[inset_0_-3px_0_var(--terracotta)]" : "text-bamboo hover:text-chalk"}`}
          >
            {g.label}
            {n ? (
              <span data-testid="waiting" data-count={g.label} aria-hidden="true" className="min-w-[20px] bg-terracotta px-[5px] py-[1px] text-center text-[11px] text-chalk tabular-nums">
                {n.toLocaleString("en-IN")}
              </span>
            ) : null}
            {n ? (
              <span id={`waiting-${g.key}`} className="sr-only">
                {n.toLocaleString("en-IN")} waiting
              </span>
            ) : null}
          </NextLink>
        );
      })}
    </nav>
  );
}

/** The pages of the group you are in, under the bar: tabs, so a group's sub-pages are never more items on the bar. */
export function GroupTabs() {
  const path = usePathname();
  const tabs = tabsOf(path);
  const here = locate(path)?.page.href;
  if (!tabs.length) return null;
  return (
    <nav aria-label="Pages in this section" className="print:hidden border-b border-basalt/12 bg-chalk">
      <ul className="mx-auto flex w-full max-w-[1560px] gap-1 overflow-x-auto px-4 md:px-8">
        {tabs.map((t) => (
          <li key={t.href}>
            <Link
              href={t.href}
              aria-current={t.href === here ? "page" : undefined}
              className={`flex min-h-11 items-center whitespace-nowrap px-3 text-[14px] no-underline ${t.href === here ? "font-medium text-basalt shadow-[inset_0_-3px_0_var(--terracotta)]" : "text-basalt/65 hover:text-basalt"}`}
            >
              {t.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** The three-line button and the panel it opens: every group with its pages, the setup, and who is signed in (`children`). */
export function MenuButton({ counts, children }: { counts: Partial<Record<string, number>>; children: ReactNode }) {
  const path = usePathname();
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === path;
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpenOn(null);
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [open]);
  const here = locate(path)?.page.href;
  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        aria-controls="site-menu"
        aria-label="Menu"
        onClick={() => setOpenOn(open ? null : path)}
        className="flex min-h-11 min-w-11 cursor-pointer items-center justify-center border border-bamboo/40 text-chalk hover:bg-chalk/10"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <path d="M3 5h14M3 10h14M3 15h14" />
        </svg>
      </button>
      {open ? (
        <div id="site-menu" role="dialog" aria-label="Menu" className="absolute inset-x-0 top-full z-40 max-h-[calc(100dvh-56px)] overflow-y-auto border-b border-basalt/30 bg-chalk text-basalt shadow-md">
          <div className="mx-auto grid w-full max-w-[1560px] gap-x-8 gap-y-6 px-4 py-6 md:grid-cols-5 md:px-8">
            {GROUPS.map((g) => (
              <section key={g.key} aria-label={g.label}>
                <h2 className="label mb-2 !text-monsoon">
                  {g.label}
                  {counts[g.key] ? <span className="ml-2 bg-terracotta px-[5px] text-chalk">{counts[g.key]}</span> : null}
                </h2>
                <ul className="grid">
                  {g.pages.map((p) => (
                    <li key={p.href}>
                      <Link href={p.href} aria-current={p.href === here ? "page" : undefined} className={`flex min-h-11 items-center text-[14.5px] no-underline ${p.href === here ? "font-medium text-basalt" : "text-basalt/75 hover:text-basalt"}`}>
                        {p.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
          <div className="mx-auto w-full max-w-[1560px] border-t border-basalt/12 px-4 py-4 md:px-8">{children}</div>
        </div>
      ) : null}
    </>
  );
}
