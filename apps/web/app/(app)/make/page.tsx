import Link from "@/components/link";
import { Body, PageHeader, Panel } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { gradeWords } from "@/lib/queries";
import { homeByClass } from "@/lib/queries-make";
import { classPacksWaiting } from "@/lib/queries-today";
import { isoWeek } from "@/lib/week";

// Make papers (goals/m1-make-papers.yaml): each class's home papers for the week, proposed by the engine from each
// child's own map; a class opens where they are approved, and where a paper is chosen for any one child.
export default async function MakePapers() {
  const [classes, packs] = await deadline(Promise.all([homeByClass(), classPacksWaiting()]));
  return (
    <>
      <PageHeader
        stage="Make papers"
        title="Make papers"
        sub="Each child's home paper for the week — one skill, from their own map — and any paper you choose for a child. Nothing prints until you approve it."
      />
      <Body>
        <Panel title="Home papers this week" aside={isoWeek()}>
          <p className="note mb-3">
            One skill per child, never a mix: the weakest they are working on, at a level where their mistake can show; a
            child with nothing red or amber is stretched one level up on their strongest skill. Open a class to approve,
            or to choose a different paper for any child.
          </p>
          <div className="overflow-x-auto">
            <table className="grid" aria-label="Home papers this week">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Grade</th>
                  <th className="text-right">Children</th>
                  <th className="text-right">Proposed</th>
                  <th className="text-right">Approved</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {classes.map((c) => (
                  <tr key={c.section}>
                    <td className="fact">{c.section}</td>
                    <td>{gradeWords(c.band)}</td>
                    <td className="num">{c.children}</td>
                    <td className="num" data-n="proposed">
                      {c.proposed}
                    </td>
                    <td className="num" data-n="approved">
                      {c.approved}
                    </td>
                    <td>
                      <Link href={`/make/${encodeURIComponent(c.section)}`}>Open</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="mt-[18px]">
          <Panel title="Class papers" aside={`${packs.length} waiting for you`}>
            <p className="note mb-3">
              A class&rsquo;s practice or assessment for a week: each child&rsquo;s own worksheet at their level, and the
              spares. Open one to check it and approve the whole class in one tap.
            </p>
            {packs.length ? (
              <ul className="grid gap-1 text-[13.5px]" aria-label="Class papers waiting for approval">
                {packs.map((p) => (
                  <li key={`${p.section}|${p.week}|${p.kind}`}>
                    <Link href={`/worksheets?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`}>
                      {p.section} · {p.week} · {p.kind === "assessment" ? "class assessment" : "class practice"}
                    </Link>{" "}
                    <span className="text-basalt/62">— {p.n} papers</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="note">Nothing waiting.</p>
            )}
            <p className="mt-3 text-[13px]">
              <Link href="/worksheets">Every class&rsquo;s papers, week by week →</Link>
            </p>
          </Panel>
        </div>
      </Body>
    </>
  );
}
