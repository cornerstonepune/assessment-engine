"use client";

import { useState } from "react";
import Link from "@/components/link";
import { Pill } from "@/components/shell";
import type { CurriculumRow } from "@/lib/queries-curriculum";
import { switchTopic } from "./topic-actions";

// The curriculum as one table (goals/u12-curriculum-table.yaml). Nimish, 2026-09-30: "When I click on grade 1, there
// is a proper table where, within grade 1, within mathematics, there are addition and subtraction, and then within
// that, there is sub. It just flows like that." A row opens the rows under it; a grade with one subject opens both, so a
// click on a grade shows its topics and a click on a topic its skills. The columns are the same at every depth.

const n = (x: number) => x.toLocaleString("en-IN");
const INDENT = ["pl-[14px]", "pl-[34px]", "pl-[54px]", "pl-[74px]"];

/** "Not taught yet", and where the person may say so, the way to say it on the same row (goals/l9-not-taught-is-said-
 *  where-it-shows.yaml): one button for the one class of the grade not yet taught it, else a choice of those classes.
 *  Said of a topic's row, every skill in it; of a skill's, that skill alone. */
function NotTaught({ row, say }: { row: CurriculumRow; say: boolean }) {
  const classes = say && row.topic ? (row.untaught ?? []) : [];
  return (
    <>
      {/* a topic's row is its skills of this grade: the topic may be taught at another grade, as the panel above says
          (goals/ux8c-one-word.yaml) */}
      <Pill tone="monsoon">{row.skill ? "not taught yet" : "not taught yet at this grade"}</Pill>
      {classes.length ? (
        <form action={switchTopic} className="inline-flex items-center gap-1">
          <input type="hidden" name="code" value={row.topic} />
          {row.skill ? <input type="hidden" name="skill" value={row.skill} /> : null}
          <input type="hidden" name="taught" value="on" />
          {classes.length === 1 ? (
            <input type="hidden" name="class" value={classes[0]} />
          ) : (
            <select name="class" aria-label="Class" className="select py-0 text-[12px]" defaultValue={classes[0]}>
              {classes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
          <button type="submit" className="chip whitespace-nowrap text-[12px]">
            {classes.length === 1 ? `Say it is taught in ${classes[0]}` : "Say it is taught"}
          </button>
        </form>
      ) : null}
    </>
  );
}

/** `levels`: the school's levels in order, the columns (lib/levels.ts). `start`: the grades it opens on, the person's own
 *  (goals/ux6-curriculum-for-the-educator.yaml), every other grade closed. */
export function CurriculumTable({ rows, levels, say = false, start = [] }: { rows: CurriculumRow[]; levels: string[]; say?: boolean; start?: string[] }) {
  const under = (id: string) => rows.filter((r) => r.parent === id);
  // a grade opens with its subject when that is the grade's only one; a topic waits for its own click
  const opening = (next: Set<string>, id: string) => {
    for (let at: string | undefined = id; at; ) {
      next.add(at);
      const only: CurriculumRow[] = under(at);
      at = only.length === 1 && only[0].depth === 1 ? only[0].id : undefined;
    }
    return next;
  };
  const [open, setOpen] = useState<Set<string>>(() => start.reduce(opening, new Set<string>()));
  const toggle = (id: string) =>
    setOpen((was) => {
      const next = new Set(was);
      if (next.has(id)) {
        next.delete(id);
        return next;
      }
      return opening(next, id);
    });
  const byId = new Map(rows.map((r) => [r.id, r]));
  const shown = rows.filter((r) => {
    for (let p = r.parent; p; p = byId.get(p)?.parent ?? null) if (!open.has(p)) return false;
    return true;
  });
  const opens = rows.filter((r) => under(r.id).length).map((r) => r.id);

  return (
    <section className="panel" aria-label="Curriculum">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-basalt/10 px-[18px] py-3">
        <span className="note">Click a grade, then a topic, to open what is under it.</span>
        <span className="flex gap-2">
          <button type="button" className="chip" onClick={() => setOpen(new Set(opens))}>
            Open everything
          </button>
          <button type="button" className="chip" onClick={() => setOpen(new Set())}>
            Close everything
          </button>
        </span>
      </div>
      <div className="min-w-0 overflow-x-auto">
        <table className="grid" aria-label="The curriculum, grade by grade">
          <thead>
            <tr>
              <th>Grade · subject · topic · skill</th>
              <th className="num">Questions</th>
              <th className="num">Worksheets</th>
              {levels.map((d) => (
                <th key={d} className="num">
                  {d}
                </th>
              ))}
              <th className="num">Children assessed</th>
              <th className="num">Assessed</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id} data-row={r.id} data-depth={r.depth} className={r.depth === 0 ? "bg-basalt/4" : undefined}>
                <td className={`min-w-[300px] max-w-[520px] ${INDENT[r.depth]}`}>
                  {under(r.id).length ? (
                    <button
                      type="button"
                      onClick={() => toggle(r.id)}
                      aria-expanded={open.has(r.id)}
                      className={`inline-flex cursor-pointer items-baseline gap-2 text-left ${r.depth === 0 ? "font-heading text-[15.5px]" : r.depth === 1 ? "text-basalt/70" : "font-medium"}`}
                    >
                      <span aria-hidden="true" className="w-3 shrink-0 text-basalt/45">
                        {open.has(r.id) ? "▾" : "▸"}
                      </span>
                      {r.label}
                    </button>
                  ) : null}
                  {under(r.id).length && r.off ? (
                    <span className="ml-2 inline-flex flex-wrap items-center gap-2 align-middle">
                      <NotTaught row={r} say={say} />
                    </span>
                  ) : null}
                  {under(r.id).length ? null : (
                    <div className="text-[13.5px]">
                      {r.href ? (
                        <Link href={r.href} className="text-basalt">
                          {r.label}
                        </Link>
                      ) : (
                        r.label
                      )}
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-basalt/62">
                        {r.sub}
                        {r.draft ? <Pill tone="bamboo">waiting for approval</Pill> : null}
                        {r.off ? <NotTaught row={r} say={say} /> : null}
                      </div>
                    </div>
                  )}
                </td>
                <td className="num">{n(r.questions)}</td>
                <td className="num">
                  {r.href ? <Link href={`${r.href}#worksheets`}>{n(r.worksheets)}</Link> : n(r.worksheets)}
                </td>
                {levels.map((d) => (
                  <td key={d} className="num" data-level={d} title={r.words?.[d]}>
                    {r.levels[d] == null ? (
                      <span className="text-basalt/35">—</span>
                    ) : r.href ? (
                      <Link href={`/library?set=${r.href.split("/").pop()}&difficulty=${d}#questions`}>{n(r.levels[d]!)}</Link>
                    ) : (
                      n(r.levels[d]!)
                    )}
                  </td>
                ))}
                <td className="num">{r.children ? r.children : <span className="text-basalt/35">—</span>}</td>
                <td className="num whitespace-nowrap">
                  {r.skills === 1 && r.depth === 3 ? (
                    r.assessed ? <Pill tone="neem">yes</Pill> : <Pill tone="monsoon">not yet</Pill>
                  ) : (
                    `${r.assessed} of ${r.skills}`
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note px-[18px] py-3">
        Questions and worksheets are the bank&rsquo;s, at this grade&rsquo;s levels; a level another grade holds is a dash. Assessed is read
        from the answers: a skill is assessed once a child of your classes has a checked answer on it; a topic or grade counts its skills assessed.
        Taught is what an educator said of their class: &ldquo;not taught yet&rdquo; marks a topic no class of the grade has been taught.
        Hover a level&rsquo;s count for what the level asks.
      </p>
    </section>
  );
}
