"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useActionState, useState } from "react";
import { find } from "@/lib/search";

// The student search on the top bar, for everyone. There is no Class or Subject control here any more (Nimish, 26 Oct 2026:
// "the filter ... in the main menu at the top just needs to go because that does not remain sacrosanct across pages"):
// each page carries its own filters (FilterBar), starting at the person's own classes and subjects.

export function Search() {
  const [found, search, busy] = useActionState(find, null);
  // the list is open on the page it was asked on: a page opened from it, or any other, puts it away
  const path = usePathname();
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === path;
  const setOpen = (yes: boolean) => setOpenOn(yes ? path : null);
  return (
    <form action={search} role="search" aria-label="Find a child or paper" onSubmit={() => setOpen(true)} className="min-w-0 max-md:flex-1 max-md:basis-0 md:shrink-0">
      <label className="sr-only" htmlFor="bar-search">
        Search
      </label>
      <div className="relative">
      <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-basalt/55">
        <circle cx="7" cy="7" r="4.6" />
        <path d="M10.6 10.6L14 14" />
      </svg>
      <input
        id="bar-search"
        name="q"
        type="search"
        className="input min-h-[40px] !w-full md:!w-[240px] !pl-9 !text-[15px] md:focus:!w-[340px] max-md:min-h-11"
        placeholder="Find a child or paper"
        autoComplete="off"
        defaultValue={found?.q}
      />
      </div>
      {open && found && !busy ? (
        <div className="absolute inset-x-2 top-full z-40 mt-1 border border-basalt/20 bg-chalk p-2 text-basalt shadow-sm md:right-8 md:left-auto md:w-[480px]">
          {found.hits.length ? (
            <ul aria-label="Found" className="grid">
              {found.hits.map((h) => (
                <li key={h.href}>
                  <Link href={h.href} onClick={() => setOpen(false)} className="block min-h-11 px-2 py-[11px] text-[13.5px] hover:bg-basalt/5">
                    {h.label}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p role="status" className="px-2 py-2 text-[13.5px]">
              {found.q ? `Nothing found for “${found.q}”: try part of a name, a roll number, a skill or a paper code (CS and six letters or numbers).` : "Type a name, a roll number, a skill or a paper code."}
            </p>
          )}
        </div>
      ) : null}
    </form>
  );
}

/** "Report a problem or suggest something", on every signed-in page (goals/feed_report_from_the_tool.yaml). It carries
 *  the page it was pressed on, and the form keeps only its path with the ids taken out. */
export function ReportLink() {
  const path = usePathname();
  const from = path.startsWith("/feedback") ? "/" : path;
  return (
    <Link
      href={`/feedback?from=${encodeURIComponent(from)}`}
      prefetch={false}
      aria-label="Report a problem or suggest something"
      title="Report a problem or suggest something"
      className="inline-flex min-h-10 shrink-0 items-center px-1 text-[13px] whitespace-nowrap text-bamboo no-underline hover:text-chalk"
    >
      <span className="max-lg:hidden">Report a problem</span>
      <span className="lg:hidden" aria-hidden="true">
        ?
      </span>
    </Link>
  );
}
