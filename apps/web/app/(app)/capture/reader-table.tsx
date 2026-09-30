"use client";

import { useState } from "react";
import { KIND } from "@/components/question";
import { Pill } from "@/components/shell";
import type { ReaderReport } from "@/lib/queries-read";

// How the reader is doing, as one table (goals/u10-tables-read-straight.yaml). Nimish, 2026-09-30: "is there just one
// view that we can have? It simply shows just one table, which can have a toggle around confidence levels, the date,
// etc. … which very clearly shows how the engine is improving or not". By day comes first: each day's share right,
// and how far it moved from the day before.

// The kinds of question on the school's own papers, read before our printed sheets; the bank's are `KIND`'s.
const EARLIER: Record<string, string> = {
  legacy_bare: "sum (earlier paper)",
  legacy_missing: "missing number (earlier paper)",
  legacy_word: "word problem (earlier paper)",
  legacy_text: "written answer (earlier paper)",
};
const kindWords = (fmt: string) => KIND[fmt] ?? EARLIER[fmt] ?? fmt.replace(/_/g, " ");
const share = (a: number, b: number) => (b ? Math.round((100 * a) / b) : null);
const pct = (n: number | null) => (n === null ? "—" : `${n}%`);
const day = (d: string) =>
  new Date(`${d}T00:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-");

const VIEWS = [
  ["day", "By day"],
  ["kind", "By kind of question"],
  ["sure", "By how sure it was"],
] as const;
type View = (typeof VIEWS)[number][0];

export function ReaderTable({ r }: { r: ReaderReport }) {
  const [view, setView] = useState<View>("day");
  // days come newest first; each day's move is against the day read before it
  const days = r.days.map((d, i) => {
    const now = share(d.right, d.stood_behind);
    const before = r.days[i + 1] ? share(r.days[i + 1].right, r.days[i + 1].stood_behind) : null;
    return { ...d, now, moved: now === null || before === null ? null : now - before };
  });
  return (
    <div className="mt-4">
      <div role="group" aria-label="Show the reader" className="mb-3 flex flex-wrap gap-2">
        {VIEWS.map(([v, words]) => (
          <button key={v} type="button" onClick={() => setView(v)} aria-pressed={view === v} className={`chip ${view === v ? "on" : ""}`}>
            {words}
          </button>
        ))}
      </div>
      {view === "sure" ? (
        <p className="note mb-2">
          An answer stands on its own only when the reader is at least {Math.round(r.floor)}% sure; below that a person checks it. When the
          bands just under that line are right nearly every time, the line can come down and fewer answers wait.
        </p>
      ) : null}
      <div className="min-w-0 overflow-x-auto">
        <table className="grid" aria-label="How the reader is doing">
          {view === "day" ? (
            <>
              <thead>
                <tr>
                  <th>Papers read on</th>
                  <th className="num">Answers checked</th>
                  <th className="num">Reader right</th>
                  <th className="num">Against the day before</th>
                  <th className="num">Gave up</th>
                </tr>
              </thead>
              <tbody>
                {days.map((d) => (
                  <tr key={d.day}>
                    <td className="fact whitespace-nowrap">{day(d.day)}</td>
                    <td className="num">{d.checked}</td>
                    <td className="num">{pct(d.now)}</td>
                    <td className="num">
                      {d.moved === null ? (
                        <span className="text-basalt/45">—</span>
                      ) : d.moved === 0 ? (
                        "no change"
                      ) : (
                        <Pill tone={d.moved > 0 ? "neem" : "terracotta"}>
                          {d.moved > 0 ? "▲" : "▼"} {Math.abs(d.moved)} points
                        </Pill>
                      )}
                    </td>
                    <td className="num">{d.gave_up}</td>
                  </tr>
                ))}
              </tbody>
            </>
          ) : view === "kind" ? (
            <>
              <thead>
                <tr>
                  <th>Kind of question</th>
                  <th className="num">Answers checked</th>
                  <th className="num">Reader right</th>
                  <th className="num">Gave up</th>
                  <th className="num">Last {r.window}</th>
                  <th className="num">Standing</th>
                </tr>
              </thead>
              <tbody>
                {r.kinds.map((k) => (
                  <tr key={k.fmt}>
                    <td>{kindWords(k.fmt)}</td>
                    <td className="num">{k.checked}</td>
                    <td className="num">{pct(share(k.right, k.checked - k.gave_up))}</td>
                    <td className="num">{k.gave_up}</td>
                    <td className="num">{k.window_right} of {k.window_n}</td>
                    <td className="num">
                      {k.trusted ? <Pill tone="neem">trusted: settles alone</Pill> : <Pill tone="bamboo">a person checks every answer</Pill>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </>
          ) : (
            <>
              <thead>
                <tr>
                  <th>Reader was this sure</th>
                  <th className="num">Answers checked</th>
                  <th className="num">Right</th>
                  <th className="num">Today</th>
                </tr>
              </thead>
              <tbody>
                {r.bands.map((b) => (
                  <tr key={b.lo}>
                    <td className="fact">{b.lo}–{Math.min(b.hi, 100)}%</td>
                    <td className="num">{b.n}</td>
                    <td className="num">{pct(share(b.right, b.n))}</td>
                    <td className="num">{b.lo >= r.floor ? <Pill tone="neem">stands alone</Pill> : <Pill tone="bamboo">a person checks</Pill>}</td>
                  </tr>
                ))}
              </tbody>
            </>
          )}
        </table>
      </div>
    </div>
  );
}
