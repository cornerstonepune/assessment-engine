"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useActionState, useRef, useState } from "react";
import { choose } from "@/lib/auth-actions";
import type { Choices } from "@/lib/choices";
import { find } from "@/lib/search";

// The two controls on the right of the top bar. The student search is for everyone. The Viewing control is for a person
// who chooses what they look at (a coordinator, or someone who teaches two subjects: lib/viewing.ts); an educator mapped to one
// class and one subject is shown neither a Subject nor a Class box (goals/nav_teacher_scope_and_todo.yaml, Nimish 24 Oct 2026).
// It is posted, and a choice shows at once on this page and every page after.

/** `chosen`: "mine" (the person's own classes), "every", or "class:" and one class. `own`: the person's own classes. */
export function Viewing({ choices, subject, chosen, own, words }: { choices: Choices; subject: string; chosen: string; own: string[]; words: string }) {
  const form = useRef<HTMLFormElement>(null);
  const submit = () => form.current?.requestSubmit();
  return (
    <details className="relative" data-viewing>
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 border border-bamboo/40 px-3 text-[13.5px] text-chalk hover:bg-chalk/10">
        <span className="text-bamboo">Viewing:</span> {words}
      </summary>
      <form ref={form} action={choose} role="group" aria-label="Viewing" className="absolute right-0 z-40 mt-1 grid w-[300px] gap-3 border border-basalt/20 bg-chalk p-4 text-basalt shadow-md">
        <label className="grid gap-1 text-[13px]" htmlFor="bar-subject">
          Subject
          <select key={subject} id="bar-subject" name="subject" defaultValue={subject} onChange={submit} className="select min-h-[40px] !w-full !text-[15px] font-medium">
            {choices.subjects.map((s) => (
              <option key={s.code} value={s.code}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-[13px]" htmlFor="bar-class">
          Class
          <select key={chosen} id="bar-class" name="class" defaultValue={chosen} onChange={submit} className="select min-h-[40px] !w-full !text-[15px] font-medium">
            {own.length ? <option value="mine">Your classes ({own.join(", ")})</option> : null}
            <option value="every">Every class</option>
            {choices.classes.map((c) => (
              <option key={c.section} value={`class:${c.section}`}>
                {c.words}
              </option>
            ))}
          </select>
        </label>
        <noscript>
          <button type="submit" className="btn secondary">
            Show
          </button>
        </noscript>
      </form>
    </details>
  );
}

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
