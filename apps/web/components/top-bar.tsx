"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useActionState, useRef, useState } from "react";
import { choose } from "@/lib/auth-actions";
import type { Choices } from "@/lib/choices";
import { find } from "@/lib/search";

// The bar at the top of every screen (goals/s1-subject-class-and-today.yaml), from the flow map Nimish locked on
// 2026-10-22: "Subject ▾ (Maths, English, …) · Class ▾ (G1, G2, … or every class) · a search box that finds a child, an
// assessment or a paper code." Choosing a subject or a class shows it at once, on this page and every page after; the
// search is posted, so what is typed never goes into an address.

/** `chosen`: "mine" (the person's own classes), "every", or "class:" and one class. `own`: the person's own classes. */
export function TopBar({ choices, subject, chosen, own }: { choices: Choices; subject: string; chosen: string; own: string[] }) {
  const form = useRef<HTMLFormElement>(null);
  const submit = () => form.current?.requestSubmit();
  return (
    <div
      role="search"
      aria-label="Subject, class and search"
      className="relative z-20 flex items-center gap-2 border-b border-basalt/12 bg-chalk px-2 py-1 md:gap-3 md:px-9 md:py-2 print:hidden"
    >
      <form ref={form} action={choose} className="flex shrink-0 items-center gap-2">
        <label className="sr-only" htmlFor="bar-subject">
          Subject
        </label>
        <select key={subject} id="bar-subject" name="subject" defaultValue={subject} onChange={submit} className="select min-h-[40px] !w-auto !text-[15px] font-medium max-md:min-h-11 max-md:max-w-[90px]">
          {choices.subjects.map((s) => (
            <option key={s.code} value={s.code}>
              {s.label}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="bar-class">
          Class
        </label>
        <select key={chosen} id="bar-class" name="class" defaultValue={chosen} onChange={submit} className="select min-h-[40px] !w-auto !text-[15px] font-medium max-md:min-h-11 max-md:max-w-[120px]">
          {own.length ? <option value="mine">Your classes ({own.join(", ")})</option> : null}
          <option value="every">Every class</option>
          {choices.classes.map((c) => (
            <option key={c.section} value={`class:${c.section}`}>
              {c.words}
            </option>
          ))}
        </select>
        <noscript>
          <button type="submit" className="btn secondary">
            Show
          </button>
        </noscript>
      </form>
      <Search />
    </div>
  );
}

function Search() {
  const [found, search, busy] = useActionState(find, null);
  // the list is open on the page it was asked on: a page opened from it, or any other, puts it away
  const path = usePathname();
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === path;
  const setOpen = (yes: boolean) => setOpenOn(yes ? path : null);
  return (
    <form action={search} onSubmit={() => setOpen(true)} className="ml-auto min-w-0 max-md:flex-1 max-md:basis-0 md:shrink-0">
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
        <div className="absolute inset-x-2 top-full mt-1 border border-basalt/20 bg-chalk p-2 shadow-sm md:right-9 md:left-auto md:w-[480px]">
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
