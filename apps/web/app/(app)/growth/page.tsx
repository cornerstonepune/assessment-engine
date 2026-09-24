import Link from "@/components/link";
import { Body, PageHeader, Panel, TONE_BG } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { classes } from "@/lib/queries-children";
import { gradeWords } from "@/lib/queries";
import { RAG_TONE, type Rag } from "@/lib/rag";
import { deadline } from "@/lib/deadline";

const COLOURS: Rag[] = ["red", "amber", "green", "grey"];

// A class card counts children — each child once, in the colour of the skill they most need help on.
const CHILD_WORDS: Record<Rag, string> = {
  red: "need help on a skill",
  amber: "practising",
  green: "have got every skill so far",
  grey: "no checked answers yet",
};

const fmtDay = (d: string) =>
  new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).replace(/ /g, "-");

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
        sub="Each grade and its classes: every child a dot, in the colour of the skill they most need help on. A class opens as its children against every skill."
      />
      <Body>
        {grades.length === 0 ? <p className="note">No child is on the roll yet.</p> : null}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
          {grades.map((band) => (
            <Panel key={band} label={gradeWords(band)} title={gradeWords(band)} aside={`${rows.filter((r) => r.band === band).length} class${rows.filter((r) => r.band === band).length === 1 ? "" : "es"}`}>
                <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {rows
                    .filter((r) => r.band === band)
                    .map((r) => (
                      <li key={r.section}>
                        <Link
                          href={`/growth/class/${encodeURIComponent(r.section)}`}
                          className="panel block p-4 text-basalt no-underline hover:bg-basalt/3"
                        >
                          <span className="font-heading text-[18px]">{r.section}</span>
                          <span className="ml-2 text-[12.5px] text-basalt/62">{r.n} {r.n === 1 ? "child" : "children"}</span>
                          <span className="mt-3 flex gap-[3px]" aria-hidden="true">
                            {COLOURS.flatMap((c) =>
                              Array.from({ length: r.kids[c] }, (_, k) => (
                                <span key={`${c}${k}`} className={`h-[14px] w-[14px] rounded-full ${TONE_BG[RAG_TONE[c]]}`} />
                              )),
                            )}
                          </span>
                          <span className="mt-2 block text-[12.5px]">
                            {COLOURS.filter((c) => r.kids[c])
                              .map((c) => `${r.kids[c]} ${CHILD_WORDS[c]}`)
                              .join(" · ")}
                          </span>
                          {r.weakest.length ? (
                            <span className="mt-2 block text-[12.5px] text-terracotta">
                              Most need help on{" "}
                              {r.weakest.map((w) => `${w.name} (${w.n} ${w.n === 1 ? "child" : "children"})`).join(", ")}
                            </span>
                          ) : null}
                          <span className="mt-2 block text-[12px] text-basalt/62">
                            {r.waiting ? `${r.waiting} answers wait on Marking` : "Nothing waits on Marking"}
                            {r.last_read ? ` · last paper read ${fmtDay(r.last_read)}` : " · no paper read yet"}
                          </span>
                        </Link>
                      </li>
                    ))}
                </ul>
            </Panel>
          ))}
          <p className="note">
            Each dot is one child, from checked papers only: red when some skill has a repeating mistake or is under half
            right, amber when the weakest skill is still being practised, green when every skill answered is got, grey
            when no paper of theirs has been checked yet.
          </p>
        </div>
      </Body>
    </>
  );
}
