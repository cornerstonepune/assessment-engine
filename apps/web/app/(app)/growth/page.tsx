import Link from "@/components/link";
import { Body, PageHeader, Panel, TONE_BG } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { classes } from "@/lib/queries-children";
import { gradeWords } from "@/lib/queries";
import { RAG_TONE, RAG_WORDS, type Rag } from "@/lib/rag";
import { deadline } from "@/lib/deadline";

const COLOURS: Rag[] = ["red", "amber", "green", "grey"];

// Children (goals/u2-children.yaml): each grade, its classes; a class opens as its children against every step.
export default async function ChildrenPage() {
  await requireStaff();
  const rows = await deadline(classes());
  const grades = [...new Set(rows.map((r) => r.band))];

  return (
    <>
      <PageHeader
        stage="Children"
        title="Children"
        sub="Each grade and its classes. A class opens as its children against every step of each skill, in red, amber, green or grey."
      />
      <Body>
        {grades.length === 0 ? <p className="note">No child is on the roll yet.</p> : null}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
          {grades.map((band) => (
            <Panel key={band} label={gradeWords(band)} title={gradeWords(band)} aside={`${rows.filter((r) => r.band === band).length} class${rows.filter((r) => r.band === band).length === 1 ? "" : "es"}`}>
                <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {rows
                    .filter((r) => r.band === band)
                    .map((r) => {
                      const seen = COLOURS.reduce((a, c) => a + r.cells[c], 0);
                      return (
                        <li key={r.section}>
                          <Link
                            href={`/growth/class/${encodeURIComponent(r.section)}`}
                            className="panel block p-4 text-basalt no-underline hover:bg-basalt/3"
                          >
                            <span className="font-heading text-[18px]">{r.section}</span>
                            <span className="ml-2 text-[12.5px] text-basalt/62">{r.n} {r.n === 1 ? "child" : "children"}</span>
                            <span className="mt-3 flex h-[8px] overflow-hidden bg-basalt/8" aria-hidden="true">
                              {seen
                                ? COLOURS.map((c) => (
                                    <span key={c} className={TONE_BG[RAG_TONE[c]]} style={{ width: `${(100 * r.cells[c]) / seen}%` }} />
                                  ))
                                : null}
                            </span>
                            <span className="mt-2 block text-[12px] text-basalt/62">
                              {seen
                                ? COLOURS.filter((c) => r.cells[c])
                                    .map((c) => `${r.cells[c]} ${RAG_WORDS[c]}`)
                                    .join(" · ")
                                : "no checked answers yet"}
                            </span>
                          </Link>
                        </li>
                      );
                    })}
                </ul>
            </Panel>
          ))}
          <p className="note">
            The colours count the steps the children have answers on, from checked papers only: red is a repeating
            mistake or under half right, amber practising, green got it, grey fewer than three answers.
          </p>
        </div>
      </Body>
    </>
  );
}
