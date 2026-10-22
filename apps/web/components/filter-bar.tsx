"use client";

import Link from "next/link";
import { useRef } from "react";

// The one filter row over every table (docs/ux-rules.md, rule 9): dropdown filters, a compact search, the filters that
// are on shown beside them with a × each, and one click to clear them all. In the same place on every page, between the
// page's heading and its table. It is a plain GET form: the filters are in the address, so a filtered list can be sent to
// a colleague, and a page needs no script of its own. Choosing a dropdown shows the result at once.
export type Filter = {
  name: string;
  label: string;
  /** The chosen value, if any. */
  value?: string;
  /** The words for "no filter": "Every class". */
  all: string;
  options: readonly (readonly [string, string])[];
};

export function FilterBar({
  action,
  filters,
  search,
  keep = {},
}: {
  /** The page's own path. */
  action: string;
  filters: readonly Filter[];
  search?: { name: string; value?: string; placeholder: string };
  /** What the page keeps while filtering (a chosen week, a tab) and never shows as a filter. */
  keep?: Record<string, string | undefined>;
}) {
  const form = useRef<HTMLFormElement>(null);
  const on = [
    ...filters.flatMap((f) => (f.value ? [{ name: f.name, label: `${f.label}: ${f.options.find(([v]) => v === f.value)?.[1] ?? f.value}` }] : [])),
    ...(search?.value ? [{ name: search.name, label: `Search: “${search.value}”` }] : []),
  ];
  const href = (without: string[]) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(keep)) if (v) q.set(k, v);
    for (const f of filters) if (f.value && !without.includes(f.name)) q.set(f.name, f.value);
    if (search?.value && !without.includes(search.name)) q.set(search.name, search.value);
    const s = q.toString();
    return s ? `${action}?${s}` : action;
  };
  const control = "min-h-[40px] border border-basalt/30 bg-chalk px-3 text-[15px] text-basalt";
  return (
    <section data-filterbar aria-label="Filters" className="mb-3">
      <form ref={form} action={action} method="get" role="search" className="flex flex-wrap items-center gap-2">
        {Object.entries(keep).map(([k, v]) => (v ? <input key={k} type="hidden" name={k} value={v} /> : null))}
        {filters.map((f) => (
          <label key={f.name} className="flex items-center gap-2 text-[13px] text-basalt/70">
            <span>{f.label}</span>
            <select name={f.name} defaultValue={f.value ?? ""} onChange={() => form.current?.requestSubmit()} className={`select ${control} !w-auto`}>
              <option value="">{f.all}</option>
              {f.options.map(([v, words]) => (
                <option key={v} value={v}>
                  {words}
                </option>
              ))}
            </select>
          </label>
        ))}
        {search ? (
          <label className="relative ml-auto flex items-center">
            <span className="sr-only">Search the list</span>
            <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" className="pointer-events-none absolute left-3 text-basalt/55">
              <circle cx="7" cy="7" r="4.6" />
              <path d="M10.6 10.6L14 14" />
            </svg>
            <input type="search" name={search.name} defaultValue={search.value ?? ""} placeholder={search.placeholder} autoComplete="off" className={`input ${control} !pl-9 !w-[240px] transition-[width] focus:!w-[340px]`} />
          </label>
        ) : null}
        <noscript>
          <button type="submit" className="btn secondary">
            Show
          </button>
        </noscript>
      </form>
      {on.length ? (
        <ul data-active-filters aria-label="Filters on" className="mt-2 flex flex-wrap items-center gap-2 text-[13px]">
          {on.map((a) => (
            <li key={a.name}>
              <Link href={href([a.name])} aria-label={`Remove filter ${a.label}`} className="inline-flex min-h-8 items-center gap-2 border border-basalt/30 bg-basalt/5 px-3 text-basalt no-underline hover:border-basalt">
                {a.label}
                <span aria-hidden="true">×</span>
              </Link>
            </li>
          ))}
          <li>
            <Link href={href(on.map((a) => a.name))} className="text-[13px]">
              Clear
            </Link>
          </li>
        </ul>
      ) : null}
    </section>
  );
}
