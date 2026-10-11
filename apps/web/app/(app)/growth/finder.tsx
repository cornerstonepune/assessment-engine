"use client";

import { useState } from "react";

/** Finds a child as it is typed, across every grade on the page (goals/ui4a-staff-and-search.yaml): a number is a roll
 *  number, anything else part of a name. It runs in the browser on the rows already shown, so what is typed is never
 *  sent anywhere: a child's name never goes into an address, and an address is what a server logs. */
export function ChildFinder({ within }: { within: string }) {
  const [words, setWords] = useState("");
  const [found, setFound] = useState<number | null>(null);

  const find = (typed: string) => {
    setWords(typed);
    const q = typed.trim().toLowerCase();
    const root = document.getElementById(within);
    if (!root) return;
    let n = 0;
    for (const row of root.querySelectorAll<HTMLTableRowElement>("tr[data-name]")) {
      const hit = !q || (/^\d+$/.test(q) ? row.dataset.roll === q : (row.dataset.name ?? "").includes(q));
      row.hidden = !hit;
      if (hit) n += 1;
    }
    // a grade with no child found is put away until the search is cleared
    for (const table of root.querySelectorAll<HTMLTableElement>("table[data-children]")) {
      const panel = table.closest("section");
      if (panel) panel.hidden = !!q && !table.querySelector("tbody tr:not([hidden])");
    }
    setFound(q ? n : null);
  };

  return (
    <div className="mb-[18px] flex flex-wrap items-end gap-x-4 gap-y-2">
      <label className="field w-full max-w-[360px]">
        <span className="label">Find a child</span>
        <input
          className="input"
          type="search"
          value={words}
          onChange={(e) => find(e.target.value)}
          placeholder="part of a name, or a roll number"
          autoComplete="off"
        />
      </label>
      {found === null ? null : (
        <p role="status" className="pb-[9px] text-[13px] text-basalt/70">
          {found === 0 ? `No child matches “${words.trim()}”.` : `${found} ${found === 1 ? "child" : "children"} found`}
        </p>
      )}
    </div>
  );
}
